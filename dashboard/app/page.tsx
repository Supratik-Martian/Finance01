"use client";

import { useState, useEffect } from "react";

import { useHeartbeat, useHeartbeatHistory, useTrades, useMarketStatus, useRealtimeTable } from "../lib/hooks";
import { MetricCards } from "../components/metric-cards";
import { EquityChart } from "../components/equity-chart";
import { PositionsTable } from "../components/positions-table";
import { AgentStatus } from "../components/agent-status";
import { RefreshCw } from "lucide-react";

export default function OverviewPage() {
  const { data: heartbeat, loading: hbLoading, refresh: refreshHb } = useHeartbeat();
  const { data: hbHistory, refresh: refreshHistory } = useHeartbeatHistory(80);
  const { data: trades, refresh: refreshTrades } = useTrades(50);
  const marketOpen = useMarketStatus();

  // Live updates via Supabase Realtime
  useRealtimeTable("agent_heartbeat", () => {
    refreshHb();
    refreshHistory();
  });
  useRealtimeTable("trades", refreshTrades);

  const [isLive, setIsLive] = useState(false);

  // Update health status every 5s
  useEffect(() => {
    if (!heartbeat) return;
    const check = () => {
      const diff = new Date().getTime() - new Date(heartbeat.timestamp).getTime();
      setIsLive(diff < 30000); // 30s threshold
    };
    check();
    const id = setInterval(check, 5000);
    return () => clearInterval(id);
  }, [heartbeat]);

  const dailyPnl = heartbeat?.daily_pnl ?? 0;
  const capital = heartbeat?.capital ?? 200_000;
  const openPos = heartbeat?.open_positions ?? 0;
  const regime = heartbeat?.regime ?? "—";
  const mode = heartbeat?.operating_mode ?? "—";
  const prices = heartbeat?.watchlist_prices ?? {};

  // Calculate win rate from trades
  const winCount = trades?.filter((t) => t.net_pnl > 0).length ?? 0;
  const totalTrades = trades?.length ?? 0;
  const winRate = totalTrades > 0 ? (winCount / totalTrades) * 100 : 0;

  return (
    <div>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: 20,
              fontWeight: 600,
              margin: 0,
              letterSpacing: "-0.02em",
            }}
          >
            Overview
          </h1>
          <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
            {new Date().toLocaleDateString("en-IN", {
              weekday: "long",
              year: "numeric",
              month: "short",
              day: "numeric",
            })}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {/* Agent Health Check */}
            {heartbeat && (
              <div style={{ display: "flex", alignItems: "center", gap: 4, marginRight: 8 }}>
                <div
                  className="pulse-dot"
                  style={{
                    background: isLive
                      ? "var(--green)"
                      : "var(--red)",
                    width: 6,
                    height: 6
                  }}
                />
                <span style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 500 }}>
                  AGENT {isLive ? "LIVE" : "OFFLINE"}
                </span>
              </div>
            )}
            <div
              className="pulse-dot"
              style={{
                background: marketOpen ? "var(--green)" : "var(--text-muted)",
              }}
            />
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              {marketOpen ? "Market Open" : "Market Closed"}
            </span>
          </div>
          <button className="btn" onClick={() => { refreshHb(); refreshHistory(); refreshTrades(); }}>
            <RefreshCw size={13} strokeWidth={1.8} />
            Refresh
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <MetricCards
        loading={hbLoading}
        dailyPnl={dailyPnl}
        capital={capital}
        openPositions={openPos}
        regime={regime}
        mode={mode}
        winRate={winRate}
        totalTrades={totalTrades}
      />

      {/* Charts + Positions Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 320px",
          gap: 16,
          marginTop: 16,
        }}
      >
        <div className="card">
          <div
            style={{
              fontSize: 13,
              fontWeight: 500,
              marginBottom: 12,
              color: "var(--text-secondary)",
            }}
          >
            Equity Curve
          </div>
          <EquityChart data={hbHistory ?? []} />
        </div>

        <AgentStatus regime={regime} mode={mode} prices={prices} />
      </div>

      {/* Positions Table */}
      <div style={{ marginTop: 16 }}>
        <PositionsTable prices={prices} />
      </div>
    </div>
  );
}
