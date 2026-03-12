# HYDRA-Lite Finance Agent

An autonomous Finance Trading Agent designed for the Indian Stock Market (NSE). It features a multi-agent "HYDRA-Lite" architecture, cloud logging via Supabase, and is ready for production deployment on Railway.

## 🚀 Key Features

-   **HYDRA-Lite Swarm**: 11 agents working in a coordinated swarm (Regime Detection, Momentum, Mean Reversion, Breakout, Sentiment, etc.).
-   **Regime Awareness**: Dynamically adjusts strategy weights based on current market conditions (Bull, Bear, Volatile, Mean Reverting).
-   **Blackboard Communication**: Agents communicate through a central blackboard for decoupeld, auditable decisions.
-   **Risk Guardian**: Dedicated agent with absolute veto power over any trade based on daily drawdown, position limits, and timing.
-   **Supabase Integration**: Real-time cloud logging for trading sessions, orders, trades, and agent heartbeats.
-   **Production Ready**: Includes `Dockerfile`, `.gitignore`, and market-hour sleep logic (wraps from 9:15 AM to 3:30 PM IST).

## 🛠 Setup Instructions

### 1. Supabase Preparation
1. Create a project at [Supabase](https://supabase.com/).
2. Open the **SQL Editor**.
3. Copy and run the contents of `database.sql` (found locally in the project root) to set up the required tables.

### 2. Environment Configuration
Create a `.env` file in the project root (based on `.env.example`):
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
KITE_API_KEY=your_zerodha_api_key
KITE_API_SECRET=your_zerodha_api_secret
INITIAL_CAPITAL=200000
PAPER_TRADING=true
```

### 3. Local Run
Install dependencies:
```bash
pip install -r requirements.txt
```
Run the agent:
```bash
python main.py
```

## 🚂 Deployment on Railway

1.  **Push to GitHub**: Push this repository to a private GitHub repo.
2.  **New Project**: On [Railway](https://railway.app/), click **New Project** -> **Deploy from GitHub repo**.
3.  **Variables**: Add your environment variables (from `.env`) in the Railway project settings.
4.  **Auto-Deploy**: Railway will detect the `Dockerfile` and deploy the agent. It will run 24/7, sleeping outside of NSE market hours.

## 📁 Project Structure

-   `main.py`: Entry point and market-hour management.
-   `src/agent.py`: Orchestrator and trading logic.
-   `src/agents/`: Individual HYDRA-Lite agents.
-   `src/db.py`: Supabase cloud logging service.
-   `src/broker.py`: Broker connection (Kite Connect / Paper Trading).
-   `src/data_stream.py`: Real-time data feed (yfinance).

## 📄 License
MIT
