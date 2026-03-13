/* ── Types matching the Supabase schema from database.sql ── */

export interface TradingSession {
    id: string;
    started_at: string;
    ended_at: string | null;
    mode: string;
    initial_capital: number;
    final_pnl: number | null;
    total_trades: number | null;
    win_rate: number | null;
    max_drawdown: number | null;
    status: string;
}

export interface Order {
    id: string;
    session_id: string | null;
    timestamp: string;
    symbol: string;
    side: string;
    quantity: number;
    order_type: string;
    price: number | null;
    status: string;
    tag: string | null;
    broker_order_id: string | null;
}

export interface Trade {
    id: string;
    session_id: string | null;
    symbol: string;
    side: string;
    quantity: number;
    entry_price: number;
    exit_price: number;
    gross_pnl: number;
    costs: number;
    net_pnl: number;
    entry_time: string;
    exit_time: string;
    hold_duration_min: number | null;
    reason: string | null;
}

export interface Heartbeat {
    id: string;
    timestamp: string;
    open_positions: number;
    daily_pnl: number;
    capital: number;
    regime: string;
    operating_mode: string;
    watchlist_prices: Record<string, number> | null;
}

export interface AgentScore {
    id: string;
    agent_name: string;
    trade_symbol: string;
    predicted_direction: string;
    actual_outcome: string;
    correct: boolean;
    timestamp: string;
}

/* ── Utility types ── */

export interface MetricCard {
    label: string;
    value: string;
    subtext?: string;
    trend?: "up" | "down" | "neutral";
}
