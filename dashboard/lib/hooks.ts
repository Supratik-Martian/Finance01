"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { supabase } from "./supabase";
import {
    getLatestHeartbeat,
    getHeartbeatHistory,
    getOrders,
    getTrades,
    getSessions,
} from "./queries";

/* ── Generic polling hook ── */

function usePolling<T>(
    fetcher: () => Promise<T>,
    intervalMs: number
): { data: T | null; loading: boolean; refresh: () => void } {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const mountedRef = useRef(true);

    const refresh = useCallback(async () => {
        try {
            const result = await fetcher();
            if (mountedRef.current) {
                setData(result);
                setLoading(false);
            }
        } catch {
            if (mountedRef.current) setLoading(false);
        }
    }, [fetcher]);

    useEffect(() => {
        mountedRef.current = true;
        // Defer initial load to avoid synchronous setState warnings in effect
        setTimeout(() => refresh(), 0);
        const id = setInterval(refresh, intervalMs);
        return () => {
            mountedRef.current = false;
            clearInterval(id);
        };
    }, [refresh, intervalMs]);

    return { data, loading, refresh };
}

/* ── Exported hooks ── */

export function useHeartbeat() {
    return usePolling(getLatestHeartbeat, 10_000);
}

export function useHeartbeatHistory(limit = 100) {
    const fetcher = useCallback(
        () => getHeartbeatHistory(limit),
        [limit]
    );
    return usePolling(fetcher, 15_000);
}

export function useOrders(limit = 50) {
    const fetcher = useCallback(() => getOrders(limit), [limit]);
    return usePolling(fetcher, 12_000);
}

export function useTrades(limit = 50) {
    const fetcher = useCallback(() => getTrades(limit), [limit]);
    return usePolling(fetcher, 12_000);
}

export function useSessions(limit = 20) {
    const fetcher = useCallback(() => getSessions(limit), [limit]);
    return usePolling(fetcher, 30_000);
}

/* ── Supabase Realtime hook for live updates ── */

export function useRealtimeTable<T>(
    table: string,
    onInsert?: (row: T) => void
) {
    useEffect(() => {
        const channel = supabase
            .channel(`realtime-${table}`)
            .on(
                "postgres_changes",
                { event: "INSERT", schema: "public", table },
                (payload) => {
                    if (onInsert) onInsert(payload.new as T);
                }
            )
            .subscribe();

        return () => {
            supabase.removeChannel(channel);
        };
    }, [table, onInsert]);
}

/* ── Market status utility ── */

export function useMarketStatus() {
    const [open, setOpen] = useState(false);

    useEffect(() => {
        function check() {
            const now = new Date();
            // Convert to IST (UTC+5:30)
            const istOffset = 5.5 * 60;
            const utcMinutes =
                now.getUTCHours() * 60 + now.getUTCMinutes();
            const istMinutes = utcMinutes + istOffset;
            const istHour = Math.floor(istMinutes / 60) % 24;
            const istMin = istMinutes % 60;
            const day = now.getUTCDay();

            // Adjust day for IST
            const istDay =
                istMinutes >= 1440 ? (day + 1) % 7 : day;

            const timeVal = istHour * 100 + istMin;
            const isWeekday = istDay >= 1 && istDay <= 5;
            const inHours = timeVal >= 915 && timeVal <= 1530;
            setOpen(isWeekday && inHours);
        }
        check();
        const id = setInterval(check, 30_000);
        return () => clearInterval(id);
    }, []);

    return open;
}
