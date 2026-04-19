from __future__ import annotations

import os
from typing import Annotated

import pyotp
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .models import APIKeyPayload, KillSwitchPayload, LoginRequest, OrderRequest, Position, RiskSettings, Trade, Verify2FARequest
from .state import AppState, build_state, get_encryption_key

app = FastAPI(title="Trade MVP API", version="0.1.0")
allowed_origins = [origin.strip() for origin in os.getenv("APP_CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

state: AppState = build_state()
fernet = Fernet(get_encryption_key())


def current_user(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    user = state.access_tokens.get(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login")
def login(payload: LoginRequest) -> dict[str, str | bool]:
    if payload.username != state.user.username or not state.user.verify_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    challenge_token = state.issue_challenge()
    return {"requires_2fa": True, "challenge_token": challenge_token}


@app.post("/auth/verify-2fa")
def verify_two_factor(payload: Verify2FARequest) -> dict[str, str]:
    username = state.challenges.pop(payload.challenge_token, None)
    if username != state.user.username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid challenge token")

    totp = pyotp.TOTP(state.user.totp_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code")

    return {"access_token": state.issue_access_token(), "token_type": "bearer"}


@app.get("/auth/2fa-setup")
def two_factor_setup(user: str = Depends(current_user)) -> dict[str, str]:
    totp = pyotp.TOTP(state.user.totp_secret)
    return {
        "username": user,
        "totp_secret": state.user.totp_secret,
        "otpauth_url": totp.provisioning_uri(name=user, issuer_name="TradeMVP"),
    }


@app.post("/secrets/api-key")
def set_api_key(payload: APIKeyPayload, _user: str = Depends(current_user)) -> dict[str, str | bool]:
    state.api_key_broker = payload.broker
    state.encrypted_api_key = fernet.encrypt(payload.api_key.encode("utf-8"))
    return {"stored": True, "broker": payload.broker}


@app.get("/secrets/api-key")
def get_api_key_status(_user: str = Depends(current_user)) -> dict[str, str | bool]:
    if not state.encrypted_api_key:
        return {"stored": False, "broker": state.api_key_broker, "masked": ""}

    raw = fernet.decrypt(state.encrypted_api_key).decode("utf-8")
    masked = "*" * max(0, len(raw) - 4) + raw[-4:]
    return {"stored": True, "broker": state.api_key_broker, "masked": masked}


def ensure_risk_ok() -> None:
    if state.kill_switch_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kill switch enabled")

    if state.daily_loss_pct() >= state.risk_settings.daily_loss_limit_pct:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Daily loss limit reached")

    if state.drawdown_pct() >= state.risk_settings.max_drawdown_pct:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Max drawdown reached")


@app.get("/risk/settings", response_model=RiskSettings)
def get_risk_settings(_user: str = Depends(current_user)) -> RiskSettings:
    return state.risk_settings


@app.put("/risk/settings", response_model=RiskSettings)
def update_risk_settings(payload: RiskSettings, _user: str = Depends(current_user)) -> RiskSettings:
    state.risk_settings = payload
    return state.risk_settings


@app.post("/risk/kill-switch")
def set_kill_switch(payload: KillSwitchPayload, _user: str = Depends(current_user)) -> dict[str, bool]:
    state.kill_switch_enabled = payload.enabled
    return {"enabled": state.kill_switch_enabled}


@app.get("/risk/status")
def risk_status(_user: str = Depends(current_user)) -> dict[str, float | bool]:
    state.update_peak()
    return {
        "kill_switch_enabled": state.kill_switch_enabled,
        "daily_loss_pct": round(state.daily_loss_pct(), 4),
        "drawdown_pct": round(state.drawdown_pct(), 4),
        "daily_loss_limit_pct": state.risk_settings.daily_loss_limit_pct,
        "max_drawdown_pct": state.risk_settings.max_drawdown_pct,
    }


@app.get("/broker/mock/account")
def mock_account(_user: str = Depends(current_user)) -> dict[str, float | str]:
    return {"mode": "paper", "currency": "USD", "cash_balance": state.cash_balance, "equity": state.current_equity()}


@app.get("/broker/mock/positions")
def mock_positions(_user: str = Depends(current_user)):
    return state.positions


@app.get("/broker/mock/trades")
def mock_trades(_user: str = Depends(current_user)):
    return state.trades


@app.post("/broker/mock/orders")
def place_mock_order(payload: OrderRequest, _user: str = Depends(current_user)) -> dict[str, str | int]:
    ensure_risk_ok()
    current_position = next((position for position in state.positions if position.symbol == payload.symbol), None)

    if payload.side == "buy":
        state.cash_balance -= payload.price * payload.quantity
        if current_position:
            original_quantity = current_position.quantity
            total_qty = original_quantity + payload.quantity
            current_position.avg_price = ((current_position.avg_price * original_quantity) + (payload.price * payload.quantity)) / total_qty
            current_position.quantity = total_qty
        else:
            state.positions.append(Position(symbol=payload.symbol, quantity=payload.quantity, avg_price=payload.price))
    else:
        state.cash_balance += payload.price * payload.quantity
        if current_position:
            current_position.quantity -= payload.quantity
            if current_position.quantity <= 0:
                state.positions = [position for position in state.positions if position.symbol != payload.symbol]

    trade_id = len(state.trades) + 1
    state.trades.append(
        Trade(
            trade_id=trade_id,
            symbol=payload.symbol,
            side=payload.side,
            quantity=payload.quantity,
            price=payload.price,
            pnl=0.0,
        )
    )
    state.update_peak()

    return {"status": "accepted", "trade_id": trade_id, "mode": "paper"}


@app.get("/dashboard/summary")
def dashboard_summary(_user: str = Depends(current_user)) -> dict[str, object]:
    return {
        "account": {"cash_balance": state.cash_balance, "equity": state.current_equity(), "currency": "USD"},
        "positions": state.positions,
        "trades": state.trades[-10:],
        "risk": {
            "kill_switch_enabled": state.kill_switch_enabled,
            "daily_loss_pct": round(state.daily_loss_pct(), 4),
            "drawdown_pct": round(state.drawdown_pct(), 4),
            "daily_loss_limit_pct": state.risk_settings.daily_loss_limit_pct,
            "max_drawdown_pct": state.risk_settings.max_drawdown_pct,
        },
    }
