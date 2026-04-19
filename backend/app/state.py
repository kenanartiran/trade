from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass, field

import pyotp

from .models import Position, RiskSettings, Trade


def hash_password(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return digest.hex()


@dataclass
class User:
    username: str
    password_hash: str
    password_salt: bytes
    totp_secret: str

    def verify_password(self, candidate: str) -> bool:
        candidate_hash = hash_password(candidate, self.password_salt)
        return hmac.compare_digest(self.password_hash, candidate_hash)


@dataclass
class AppState:
    user: User
    access_tokens: dict[str, str] = field(default_factory=dict)
    challenges: dict[str, str] = field(default_factory=dict)
    encrypted_api_key: bytes | None = None
    api_key_broker: str = "mock"
    risk_settings: RiskSettings = field(default_factory=RiskSettings)
    kill_switch_enabled: bool = False
    cash_balance: float = 10_000.0
    start_of_day_equity: float = 10_000.0
    equity_peak: float = 10_000.0
    positions: list[Position] = field(
        default_factory=lambda: [
            Position(symbol="AAPL", quantity=2, avg_price=190.0),
            Position(symbol="MSFT", quantity=1, avg_price=410.0),
        ]
    )
    trades: list[Trade] = field(
        default_factory=lambda: [
            Trade(trade_id=1, symbol="AAPL", side="buy", quantity=1, price=188.0, pnl=0.0),
            Trade(trade_id=2, symbol="MSFT", side="buy", quantity=1, price=402.0, pnl=0.0),
        ]
    )

    def issue_challenge(self) -> str:
        challenge = secrets.token_urlsafe(24)
        self.challenges[challenge] = self.user.username
        return challenge

    def issue_access_token(self) -> str:
        token = secrets.token_urlsafe(32)
        self.access_tokens[token] = self.user.username
        return token

    def current_equity(self) -> float:
        return self.cash_balance

    def update_peak(self) -> None:
        equity = self.current_equity()
        if equity > self.equity_peak:
            self.equity_peak = equity

    def daily_loss_pct(self) -> float:
        if self.start_of_day_equity <= 0:
            return 0.0
        loss = max(0.0, self.start_of_day_equity - self.current_equity())
        return (loss / self.start_of_day_equity) * 100

    def drawdown_pct(self) -> float:
        if self.equity_peak <= 0:
            return 0.0
        drawdown = max(0.0, self.equity_peak - self.current_equity())
        return (drawdown / self.equity_peak) * 100


def build_state() -> AppState:
    default_user = os.getenv("APP_USERNAME", "trader")
    default_password = os.getenv("APP_PASSWORD", "change-me")
    provided_secret = os.getenv("APP_TOTP_SECRET")
    totp_secret = provided_secret if provided_secret else pyotp.random_base32()
    salt = secrets.token_bytes(16)
    user = User(
        username=default_user,
        password_hash=hash_password(default_password, salt),
        password_salt=salt,
        totp_secret=totp_secret,
    )
    return AppState(user=user)


def get_encryption_key() -> bytes:
    configured = os.getenv("APP_ENCRYPTION_KEY")
    if configured:
        base64.urlsafe_b64decode(configured)
        return configured.encode("utf-8")
    return base64.urlsafe_b64encode(secrets.token_bytes(32))
