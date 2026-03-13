"use client";

import { useTrades, useRealtimeTable } from "../../lib/hooks";
import { Download, Inbox } from "lucide-react";

export default function TradesPage() {
    const { data: trades, loading, refresh } = useTrades(100);

    // Live updates
    useRealtimeTable("trades", refresh);

    const totalPnl = trades?.reduce((s, t) => s + t.net_pnl, 0) ?? 0;
    const winners = trades?.filter((t) => t.net_pnl > 0).length ?? 0;
    const losers = trades?.filter((t) => t.net_pnl < 0).length ?? 0;

    function downloadCsv() {
        if (!trades || trades.length === 0) return;
        const headers = [
            "Symbol", "Side", "Qty", "Entry", "Exit",
            "Gross P&L", "Costs", "Net P&L", "Reason",
            "Entry Time", "Exit Time",
        ];
        const rows = trades.map((t) => [
            t.symbol, t.side, t.quantity, t.entry_price, t.exit_price,
            t.gross_pnl, t.costs, t.net_pnl, t.reason ?? "",
            t.entry_time, t.exit_time,
        ]);
        const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `trades_${new Date().toISOString().split("T")[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    return (
        <div>
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: 20,
                }}
            >
                <div>
                    <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Trades</h1>
                    <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                        {winners}W / {losers}L — Net: ₹
                        {totalPnl.toLocaleString("en-IN", {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                        })}
                    </p>
                </div>
                <button className="btn" onClick={downloadCsv}>
                    <Download size={13} strokeWidth={1.8} />
                    Export CSV
                </button>
            </div>

            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                {loading ? (
                    <div style={{ padding: 48, textAlign: "center" }}>
                        <div
                            className="skeleton"
                            style={{ height: 16, width: "60%", margin: "0 auto 8px" }}
                        />
                        <div
                            className="skeleton"
                            style={{ height: 16, width: "40%", margin: "0 auto" }}
                        />
                    </div>
                ) : !trades || trades.length === 0 ? (
                    <div className="empty-state">
                        <Inbox size={28} strokeWidth={1.2} />
                        <p style={{ fontSize: 13 }}>No trades recorded yet.</p>
                    </div>
                ) : (
                    <div style={{ overflowX: "auto" }}>
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Side</th>
                                    <th>Qty</th>
                                    <th style={{ textAlign: "right" }}>Entry</th>
                                    <th style={{ textAlign: "right" }}>Exit</th>
                                    <th style={{ textAlign: "right" }}>Net P&L</th>
                                    <th style={{ textAlign: "right" }}>Costs</th>
                                    <th>Reason</th>
                                    <th>Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                {trades.map((t) => (
                                    <tr key={t.id}>
                                        <td style={{ fontWeight: 500 }}>{t.symbol}</td>
                                        <td>
                                            <span
                                                className={`badge ${t.side === "BUY" ? "badge-green" : "badge-red"}`}
                                            >
                                                {t.side}
                                            </span>
                                        </td>
                                        <td>{t.quantity}</td>
                                        <td
                                            style={{
                                                textAlign: "right",
                                                fontFamily: "var(--font-geist-mono), monospace",
                                            }}
                                        >
                                            ₹{t.entry_price.toFixed(2)}
                                        </td>
                                        <td
                                            style={{
                                                textAlign: "right",
                                                fontFamily: "var(--font-geist-mono), monospace",
                                            }}
                                        >
                                            ₹{t.exit_price.toFixed(2)}
                                        </td>
                                        <td
                                            style={{
                                                textAlign: "right",
                                                fontWeight: 500,
                                                fontFamily: "var(--font-geist-mono), monospace",
                                                color: t.net_pnl >= 0 ? "var(--green)" : "var(--red)",
                                            }}
                                        >
                                            {t.net_pnl >= 0 ? "+" : ""}₹{t.net_pnl.toFixed(0)}
                                        </td>
                                        <td
                                            style={{
                                                textAlign: "right",
                                                fontSize: 11,
                                                color: "var(--text-muted)",
                                            }}
                                        >
                                            ₹{t.costs.toFixed(0)}
                                        </td>
                                        <td style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                                            {t.reason ?? "—"}
                                        </td>
                                        <td style={{ fontSize: 11, color: "var(--text-muted)" }}>
                                            {new Date(t.exit_time).toLocaleTimeString("en-IN", {
                                                hour: "2-digit",
                                                minute: "2-digit",
                                            })}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
