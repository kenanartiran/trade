# Trade MVP Prototype (Private Web App)

MVP prototype for a private trading web app with:
- **Frontend:** Next.js dashboard/login UI
- **Backend:** FastAPI with mock broker endpoints (prepared for later IBKR adapter)
- **Security:** username/password login, TOTP 2FA, encrypted API-key storage
- **Risk controls:** stop-loss/take-profit-required order schema, daily-loss limit, drawdown-stop, kill-switch
- **Paper mode:** mock account/positions/trades only (no payout/withdrawal function)

## Project Structure

- `/frontend` – Next.js app
- `/backend` – FastAPI app + tests
- `/docker-compose.yml` – local full-stack startup

## Quick Start (Docker Compose)

```bash
docker compose up --build
```

Then open:
- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`

Default demo credentials:
- username: `trader`
- password: `change-me`

Default demo TOTP secret in compose: `JBSWY3DPEHPK3PXP`
(use any authenticator app or generate a code in CLI)

## Local Development (without Docker)

### Backend

```bash
cd /home/runner/work/trade/trade/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd /home/runner/work/trade/trade/frontend
cp .env.example .env.local
npm install
npm run dev
```

## Tests

```bash
cd /home/runner/work/trade/trade/backend
python -m pytest -q
```

## Important Notes

- This MVP is **paper-trading oriented** with **mock endpoints** for future broker integration.
- API keys are encrypted server-side before storage.
- Withdrawal/payout functionality is intentionally not implemented.
