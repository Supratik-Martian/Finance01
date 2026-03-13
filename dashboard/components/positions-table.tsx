"use client";

import { Inbox } from "lucide-react";

interface Props {
    prices: Record<string, number>;
}

export function PositionsTable({ prices }: Props) {
    const entries = Object.entries(prices);

    if (entries.length === 0) {
        return (
            <div className="card">
                <div
                    style={{
                        fontSize: 13,
                        fontWeight: 500,
                        marginBottom: 12,
                        color: "var(--text-secondary)",
                    }}
                >
                    Watchlist Prices
                </div>
                <div className="empty-state" style={{ padding: "32px 24px" }}>
                    <Inbox size={24} strokeWidth={1.2} />
                    <p style={{ fontSize: 12 }}>No live prices available.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="card" style={{ padding: "16px 0" }}>
            <div
                style={{
                    fontSize: 13,
                    fontWeight: 500,
                    marginBottom: 8,
                    color: "var(--text-secondary)",
                    padding: "0 16px",
                }}
            >
                Watchlist Prices
            </div>
            <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th style={{ textAlign: "right" }}>LTP (₹)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {entries
                            .sort(([a], [b]) => a.localeCompare(b))
                            .map(([symbol, price]) => (
                                <tr key={symbol}>
                                    <td style={{ fontWeight: 500 }}>{symbol}</td>
                                    <td
                                        style={{
                                            textAlign: "right",
                                            fontFamily: "var(--font-geist-mono), monospace",
                                        }}
                                    >
                                        ₹{price.toLocaleString("en-IN", {
                                            minimumFractionDigits: 2,
                                            maximumFractionDigits: 2,
                                        })}
                                    </td>
                                </tr>
                            ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
