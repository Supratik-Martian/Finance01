import { supabase } from "./supabase";
import type {
    TradingSession,
    Order,
    Trade,
    Heartbeat,
    AgentScore,
} from "./types";

/* ── Session queries ── */

export async function getLatestSession(): Promise<TradingSession | null> {
    const { data, error } = await supabase
        .from("trading_sessions")
        .select("*")
        .order("started_at", { ascending: false })
        .limit(1)
        .single();

    if (error) {
        console.error("Failed to fetch session:", error.message);
        return null;
    }
    return data as TradingSession;
}

export async function getSessions(
    limit = 20
): Promise<TradingSession[]> {
    const { data, error } = await supabase
        .from("trading_sessions")
        .select("*")
        .order("started_at", { ascending: false })
        .limit(limit);

    if (error) {
        console.error("Failed to fetch sessions:", error.message);
        return [];
    }
    return (data ?? []) as TradingSession[];
}

/* ── Heartbeat queries ── */

export async function getLatestHeartbeat(): Promise<Heartbeat | null> {
    const { data, error } = await supabase
        .from("agent_heartbeat")
        .select("*")
        .order("timestamp", { ascending: false })
        .limit(1)
        .single();

    if (error) {
        console.error("Failed to fetch heartbeat:", error.message);
        return null;
    }
    return data as Heartbeat;
}

export async function getHeartbeatHistory(
    limit = 100
): Promise<Heartbeat[]> {
    const { data, error } = await supabase
        .from("agent_heartbeat")
        .select("*")
        .order("timestamp", { ascending: false })
        .limit(limit);

    if (error) {
        console.error("Failed to fetch heartbeat history:", error.message);
        return [];
    }
    return (data ?? []) as Heartbeat[];
}

/* ── Order queries ── */

export async function getOrders(limit = 50): Promise<Order[]> {
    const { data, error } = await supabase
        .from("orders")
        .select("*")
        .order("timestamp", { ascending: false })
        .limit(limit);

    if (error) {
        console.error("Failed to fetch orders:", error.message);
        return [];
    }
    return (data ?? []) as Order[];
}

/* ── Trade queries ── */

export async function getTrades(limit = 50): Promise<Trade[]> {
    const { data, error } = await supabase
        .from("trades")
        .select("*")
        .order("exit_time", { ascending: false })
        .limit(limit);

    if (error) {
        console.error("Failed to fetch trades:", error.message);
        return [];
    }
    return (data ?? []) as Trade[];
}

/* ── Agent score queries ── */

export async function getAgentScores(
    limit = 200
): Promise<AgentScore[]> {
    const { data, error } = await supabase
        .from("agent_scores")
        .select("*")
        .order("timestamp", { ascending: false })
        .limit(limit);

    if (error) {
        console.error("Failed to fetch agent scores:", error.message);
        return [];
    }
    return (data ?? []) as AgentScore[];
}
