# QuantLab Pro — paper-only developer preview

**Not a production trading bot.** No wallet binding, no signing, no real transactions. Never provide seed phrases or private keys. The Windows app is not a background worker; Docker runs the optional background scanner.

## Windows
Install Python 3.12+; copy `.env.example` to `.env`, replace the token with a long random value; double-click `启动Windows.bat`. Open http://localhost:8501. Windows mode runs manual scans; it does not run the worker by default.

## VPS / cloud
Install Docker Compose. Copy `.env.example` to `.env` and replace the token. Run `docker compose up -d --build`. Dashboard binds **127.0.0.1:8501 only**. Access it over SSH tunnel: `ssh -L 8501:localhost:8501 USER@VPS`. Do not expose it publicly without HTTPS, reverse-proxy authentication, firewall and operational review. The worker runs once per minute and pauses unless enabled in UI.

## Actual coverage and limitations
- BNB Chain, Ethereum and Solana: DEX Screener token-profile discovery and pair lookups, not comprehensive chain-level new pool subscription. No guarantee that a new token is found promptly.
- Risk checks: liquidity/volume/FDV/age plus optional GoPlus flags for EVM. Solana is **not** security verified and cannot pass manual paper BUY. EVM check is incomplete and cannot guarantee sellability or safety.
- Paper portfolio: SQLite balances, positions, orders, conservative exposure/order/cooldown caps, configurable simulated fee/slippage. Not an exchange-matching engine. Marks use last observed price, which may be stale.
- Automated scanner: samples watched token prices and generates basic RSI/MA signals after 15 ticks. It can simulate stop-loss/take-profit or RSI exits of existing paper positions. Autonomous BUY is intentionally disabled until end-to-end per-chain risk validation and independent testing exist.
- Follow trading: watch-address transaction ingestion and copy-execution **not implemented**.
- Grid: a separate grid order state machine **not implemented**.
- Arbitrage: executable multi-pool quote, atomicity and MEV handling **not implemented**.
- AI: trained forecasting and walk-forward evaluation **not implemented**.
- Wallet: Bitget Wallet pairing, key custody and signing **not implemented**. Cold wallet address alone cannot sign orders.
- Daily-loss setting exists as configuration but circuit breaker is **not implemented**. Do not treat it as enforced. Network/API errors are logged, and failed checks fail closed for new buys.

## Tests
`python -m pytest -q`

## Data sources
https://docs.dexscreener.com/api/reference
https://docs.gopluslabs.io/reference/token-security-api
Read provider terms, rate limits and chain coverage before production use.
