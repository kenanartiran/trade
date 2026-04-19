'use client';

import { FormEvent, useMemo, useState } from 'react';

type DashboardData = {
  account: { cash_balance: number; equity: number; currency: string };
  positions: Array<{ symbol: string; quantity: number; avg_price: number }>;
  trades: Array<{ trade_id: number; symbol: string; side: string; quantity: number; price: number; pnl: number }>;
  risk: {
    kill_switch_enabled: boolean;
    daily_loss_pct: number;
    drawdown_pct: number;
    daily_loss_limit_pct: number;
    max_drawdown_pct: number;
  };
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export default function Home() {
  const [username, setUsername] = useState('trader');
  const [password, setPassword] = useState('change-me');
  const [challengeToken, setChallengeToken] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [token, setToken] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [status, setStatus] = useState('Ready');

  const authHeader = useMemo(
    () => (token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : undefined),
    [token],
  );

  async function login(e: FormEvent) {
    e.preventDefault();
    setStatus('Logging in...');
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      setStatus('Login failed');
      return;
    }

    const data = await response.json();
    setChallengeToken(data.challenge_token);
    setStatus('2FA code required');
  }

  async function verify2FA(e: FormEvent) {
    e.preventDefault();
    setStatus('Verifying 2FA...');
    const response = await fetch(`${API_URL}/auth/verify-2fa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ challenge_token: challengeToken, code: otpCode }),
    });

    if (!response.ok) {
      setStatus('Invalid 2FA code');
      return;
    }

    const data = await response.json();
    setToken(data.access_token);
    setStatus('Authenticated');
  }

  async function loadDashboard() {
    if (!authHeader) return;
    const response = await fetch(`${API_URL}/dashboard/summary`, { headers: authHeader });
    if (!response.ok) {
      setStatus('Dashboard load failed');
      return;
    }
    const data = await response.json();
    setDashboard(data);
    setStatus('Dashboard updated');
  }

  async function storeApiKey() {
    if (!authHeader) return;
    const response = await fetch(`${API_URL}/secrets/api-key`, {
      method: 'POST',
      headers: authHeader,
      body: JSON.stringify({ broker: 'ibkr', api_key: apiKey }),
    });

    if (!response.ok) {
      setStatus('API key save failed');
      return;
    }

    setStatus('Encrypted API key saved');
    setApiKey('');
  }

  async function toggleKillSwitch(enabled: boolean) {
    if (!authHeader) return;
    const response = await fetch(`${API_URL}/risk/kill-switch`, {
      method: 'POST',
      headers: authHeader,
      body: JSON.stringify({ enabled }),
    });

    if (!response.ok) {
      setStatus('Kill switch update failed');
      return;
    }

    setStatus(enabled ? 'Kill switch enabled' : 'Kill switch disabled');
    await loadDashboard();
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-4 p-8">
      <h1 className="text-3xl font-bold">Private Trading App MVP (Paper Mode)</h1>
      <p className="text-sm text-gray-500">Status: {status}</p>

      {!challengeToken && (
        <form className="grid gap-3 rounded border p-4" onSubmit={login}>
          <h2 className="font-semibold">1) Login</h2>
          <input className="rounded border p-2" value={username} onChange={(e) => setUsername(e.target.value)} />
          <input
            className="rounded border p-2"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button className="rounded bg-black px-4 py-2 text-white" type="submit">
            Login
          </button>
        </form>
      )}

      {challengeToken && !token && (
        <form className="grid gap-3 rounded border p-4" onSubmit={verify2FA}>
          <h2 className="font-semibold">2) Verify 2FA</h2>
          <input
            className="rounded border p-2"
            placeholder="6-digit code"
            value={otpCode}
            onChange={(e) => setOtpCode(e.target.value)}
          />
          <button className="rounded bg-black px-4 py-2 text-white" type="submit">
            Verify
          </button>
        </form>
      )}

      {token && (
        <section className="grid gap-3 rounded border p-4">
          <h2 className="font-semibold">3) Dashboard</h2>
          <div className="flex flex-wrap gap-2">
            <button className="rounded bg-black px-4 py-2 text-white" onClick={loadDashboard} type="button">
              Refresh Dashboard
            </button>
            <button className="rounded bg-red-700 px-4 py-2 text-white" onClick={() => toggleKillSwitch(true)} type="button">
              Enable Kill-Switch
            </button>
            <button
              className="rounded bg-green-700 px-4 py-2 text-white"
              onClick={() => toggleKillSwitch(false)}
              type="button"
            >
              Disable Kill-Switch
            </button>
          </div>

          <div className="grid gap-2">
            <h3 className="font-medium">Store Broker API Key (encrypted backend storage)</h3>
            <input
              className="rounded border p-2"
              placeholder="Broker API key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
            <button className="rounded bg-black px-4 py-2 text-white" onClick={storeApiKey} type="button">
              Save API Key
            </button>
          </div>

          {dashboard && (
            <div className="grid gap-4">
              <div className="rounded bg-gray-100 p-3">
                <h3 className="font-medium">Account</h3>
                <p>
                  Balance: {dashboard.account.cash_balance.toFixed(2)} {dashboard.account.currency}
                </p>
                <p>Equity: {dashboard.account.equity.toFixed(2)}</p>
              </div>

              <div className="rounded bg-gray-100 p-3">
                <h3 className="font-medium">Risk</h3>
                <p>Kill-Switch: {dashboard.risk.kill_switch_enabled ? 'ON' : 'OFF'}</p>
                <p>Daily Loss: {dashboard.risk.daily_loss_pct.toFixed(2)}%</p>
                <p>Drawdown: {dashboard.risk.drawdown_pct.toFixed(2)}%</p>
              </div>

              <div className="rounded bg-gray-100 p-3">
                <h3 className="font-medium">Positions</h3>
                <ul className="list-disc pl-5">
                  {dashboard.positions.map((position) => (
                    <li key={position.symbol}>
                      {position.symbol}: {position.quantity} @ {position.avg_price}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded bg-gray-100 p-3">
                <h3 className="font-medium">Trades</h3>
                <ul className="list-disc pl-5">
                  {dashboard.trades.map((trade) => (
                    <li key={trade.trade_id}>
                      #{trade.trade_id} {trade.side} {trade.quantity} {trade.symbol} @ {trade.price}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
