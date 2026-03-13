"use client";

import { useHeartbeatHistory } from "@/lib/hooks";
import { Inbox } from "lucide-react";

const AGENT_NAMES = [
    { key: "regime", label: "Regime Detector", desc: "ADX + Hurst + ATR ensemble" },
    { key: "momentum", label: "Momentum", desc: "EMA crossover + RSI + ADX" },
    { key: "mean_reversion", label: "Mean Reversion", desc: "VWAP + Bollinger + Z-score" },
    { key: "breakout", label: "Breakout", desc: "Donchian channels + volume" },
    { key: "sentiment", label: "Sentiment", desc: "yfinance news keyword scoring" },
    { key: "contrarian", label: "Contrarian", desc: "RSI extremes + crowding" },
    { key: "bull", label: "Bull Aggregator", desc: "Aggregates LONG evidence" },
    { key: "bear", label: "Bear Aggregator", desc: "Aggregates SHORT + risks" },
    { key: "risk_guardian", label: "Risk Guardian", desc: "Veto power: drawdown, limits, time" },
    { key: "orchestrator", label: "Orchestrator", desc: "Dynamic weighting + debate resolution" },
];

export default function AgentsPage() {
    const { data: history } = useHeartbeatHistory(30);

    // Extract regime timeline from heartbeat history
    const regimeTimeline = (history ?? [])
        .slice()
        .reverse()
        .map((h) => ({
            time: new Date(h.timestamp).toLocaleTimeString("en-IN", {
                hour: "2-digit",
                minute: "2-digit",
            }),
            regime: h.regime,
            mode: h.operating_mode,
        }));

    // Deduplicate consecutive identical regimes
    const deduped = regimeTimeline.filter(
        (r, i) => i === 0 || r.regime !== regimeTimeline[i - 1].regime
    );

    return (
        <div>
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Agent Swarm</h1>
                <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                    10 agents working in coordinated pipeline
                </p>
            </div>

            {/* Agent table */}
            <div className="card" style={{ padding: 0, overflow: "hidden", marginBottom: 16 }}>
                <table className="data-table">
                    <thead>
                        <tr>
                            <th style={{ width: 40 }}>#</th>
                            <th>Agent</th>
                            <th>Strategy</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {AGENT_NAMES.map((a, i) => (
                            <tr key={a.key}>
                                <td style={{ color: "var(--text-muted)", fontSize: 11 }}>
                                    {String(i + 1).padStart(2, "0")}
                                </td>
                                <td style={{ fontWeight: 500 }}>{a.label}</td>
                                <td style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                                    {a.desc}
                                </td>
                                <td>
                                    <div
                                        style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: 6,
                                        }}
                                    >
                                        <div
                                            style={{
                                                width: 6,
                                                height: 6,
                                                borderRadius: "50%",
                                                background: "var(--green)",
                                            }}
                                        />
                                        <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                                            Active
                                        </span>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Regime Timeline */}
            <div className="card">
                <div
                    style={{
                        fontSize: 13,
                        fontWeight: 500,
                        marginBottom: 12,
                        color: "var(--text-secondary)",
                    }}
                >
                    Regime History
                </div>

                {deduped.length === 0 ? (
                    <div className="empty-state" style={{ padding: "24px 0" }}>
                        <Inbox size={24} strokeWidth={1.2} />
                        <p style={{ fontSize: 12 }}>No regime transitions recorded yet.</p>
                    </div>
                ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {deduped.map((r, i) => (
                            <div
                                key={i}
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 12,
                                    padding: "6px 0",
                                    borderBottom:
                                        i < deduped.length - 1 ? "1px solid #f3f4f6" : "none",
                                }}
                            >
                                <span
                                    style={{
                                        fontSize: 11,
                                        color: "var(--text-muted)",
                                        minWidth: 48,
                                        fontFamily: "var(--font-geist-mono), monospace",
                                    }}
                                >
                                    {r.time}
                                </span>
                                <span
                                    className={`badge ${r.regime.toLowerCase().includes("bull")
                                            ? "badge-green"
                                            : r.regime.toLowerCase().includes("bear")
                                                ? "badge-red"
                                                : r.regime.toLowerCase().includes("mean")
                                                    ? "badge-blue"
                                                    : "badge-gray"
                                        }`}
                                >
                                    {r.regime.replace(/_/g, " ")}
                                </span>
                                <span
                                    style={{
                                        fontSize: 11,
                                        color: "var(--text-muted)",
                                    }}
                                >
                                    → {r.mode.replace(/_/g, " ")}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
