"use client";

import { useOrders, useRealtimeTable } from "@/lib/hooks";
import { Inbox } from "lucide-react";

export default function OrdersPage() {
    const { data: orders, loading, refresh } = useOrders(100);

    // Live updates
    useRealtimeTable("orders", refresh);

    return (
        <div>
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Orders</h1>
                <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                    {orders?.length ?? 0} orders logged
                </p>
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
                ) : !orders || orders.length === 0 ? (
                    <div className="empty-state">
                        <Inbox size={28} strokeWidth={1.2} />
                        <p style={{ fontSize: 13 }}>No orders placed yet.</p>
                    </div>
                ) : (
                    <div style={{ overflowX: "auto" }}>
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Time</th>
                                    <th>Symbol</th>
                                    <th>Side</th>
                                    <th>Type</th>
                                    <th style={{ textAlign: "right" }}>Qty</th>
                                    <th style={{ textAlign: "right" }}>Price</th>
                                    <th>Status</th>
                                    <th>Tag</th>
                                </tr>
                            </thead>
                            <tbody>
                                {orders.map((o) => (
                                    <tr key={o.id}>
                                        <td style={{ fontSize: 11, color: "var(--text-muted)" }}>
                                            {new Date(o.timestamp).toLocaleTimeString("en-IN", {
                                                hour: "2-digit",
                                                minute: "2-digit",
                                                second: "2-digit",
                                            })}
                                        </td>
                                        <td style={{ fontWeight: 500 }}>{o.symbol}</td>
                                        <td>
                                            <span
                                                className={`badge ${o.side === "BUY" ? "badge-green" : "badge-red"}`}
                                            >
                                                {o.side}
                                            </span>
                                        </td>
                                        <td style={{ fontSize: 11 }}>{o.order_type}</td>
                                        <td style={{ textAlign: "right" }}>{o.quantity}</td>
                                        <td
                                            style={{
                                                textAlign: "right",
                                                fontFamily: "var(--font-geist-mono), monospace",
                                            }}
                                        >
                                            {o.price ? `₹${o.price.toFixed(2)}` : "MKT"}
                                        </td>
                                        <td>
                                            <span
                                                className={`badge ${o.status === "COMPLETE"
                                                    ? "badge-green"
                                                    : o.status === "REJECTED"
                                                        ? "badge-red"
                                                        : "badge-gray"
                                                    }`}
                                            >
                                                {o.status}
                                            </span>
                                        </td>
                                        <td style={{ fontSize: 11, color: "var(--text-muted)" }}>
                                            {o.tag ?? "—"}
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
