from enum import Enum

from pydantic import BaseModel, Field


class Side(str, Enum):
    buy = "buy"
    sell = "sell"


class LoginRequest(BaseModel):
    username: str
    password: str


class Verify2FARequest(BaseModel):
    challenge_token: str
    code: str = Field(min_length=6, max_length=6)


class APIKeyPayload(BaseModel):
    broker: str = Field(default="mock")
    api_key: str = Field(min_length=8)


class RiskSettings(BaseModel):
    daily_loss_limit_pct: float = Field(default=2.0, gt=0, le=100)
    max_drawdown_pct: float = Field(default=10.0, gt=0, le=100)


class KillSwitchPayload(BaseModel):
    enabled: bool


class OrderRequest(BaseModel):
    symbol: str = Field(min_length=1)
    side: Side
    quantity: float = Field(gt=0)
    price: float = Field(default=100.0, gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: float = Field(gt=0)


class Position(BaseModel):
    symbol: str
    quantity: float
    avg_price: float


class Trade(BaseModel):
    trade_id: int
    symbol: str
    side: Side
    quantity: float
    price: float
    pnl: float
