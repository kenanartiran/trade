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

## Beginner Guide: Test UI without Backend

You can test the frontend UI first, without starting the backend.

1. Open Terminal
2. Go to your cloned project folder (use your own path, not `/home/runner/...`):
   ```bash
   cd <YOUR_PATH>/trade/frontend
   ```
   Example:
   ```bash
   cd ~/trade/frontend
   ```
3. Install dependencies:
   ```bash
   npm install
   ```
4. Start frontend:
   ```bash
   npm run dev
   ```
5. Open `http://localhost:3000`

Important:
- The page/UI loads.
- Login, 2FA, and dashboard data need a running backend API.

## Full Test (Recommended)

If you want to test everything (frontend + backend), run:

```bash
cd <YOUR_PATH>/trade
docker compose up --build
```

Then open:
- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`

Demo login:
- username: `trader`
- password: `change-me`

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Tests

```bash
cd backend
python -m pytest -q
```

## Important Notes

- This MVP is **paper-trading oriented** with **mock endpoints** for future broker integration.
- API keys are encrypted server-side before storage.
- Withdrawal/payout functionality is intentionally not implemented.
