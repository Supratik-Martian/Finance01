"use client";

import {
    ResponsiveContainer,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    Tooltip,
    CartesianGrid,
} from "recharts";
import type { Heartbeat } from "@/lib/types";
import { Inbox } from "lucide-react";

interface Props {
    data: Heartbeat[];
}

export function EquityChart({ data }: Props) {
    if (!data || data.length === 0) {
        return (
            <div className="empty-state" style={{ height: 240 }}>
                <Inbox size={28} strokeWidth={1.2} />
                <p style={{ fontSize: 13 }}>No heartbeat data yet.</p>
                <p style={{ fontSize: 11 }}>Data will appear once the agent starts trading.</p>
            </div>
        );
    }

    // Reverse to oldest→newest, compute equity
    const sorted = [...data].reverse();
    const baseCapital = sorted[0]?.capital ?? 200_000;

    const chartData = sorted.map((h) => ({
        time: new Date(h.timestamp).toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
        }),
        equity: baseCapital + h.daily_pnl,
        pnl: h.daily_pnl,
    }));

    const minEquity = Math.min(...chartData.map((d) => d.equity));
    const maxEquity = Math.max(...chartData.map((d) => d.equity));
    const pad = (maxEquity - minEquity) * 0.15 || 1000;

    const isPositive = chartData[chartData.length - 1]?.pnl >= 0;
    const color = isPositive ? "#16a34a" : "#dc2626";

    return (
        <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <defs>
                    <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={color} stopOpacity={0.12} />
                        <stop offset="100%" stopColor={color} stopOpacity={0} />
                    </linearGradient>
                </defs>
                <CartesianGrid stroke="#f3f4f6" strokeDasharray="3 3" vertical={false} />
                <XAxis
                    dataKey="time"
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    axisLine={false}
                    tickLine={false}
                    interval="preserveStartEnd"
                />
                <YAxis
                    domain={[minEquity - pad, maxEquity + pad]}
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v: number) =>
                        `₹${(v / 1000).toFixed(0)}k`
                    }
                    width={56}
                />
                <Tooltip
                    contentStyle={{
                        fontSize: 12,
                        border: "1px solid #e5e7eb",
                        borderRadius: 6,
                        boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
                    }}
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    formatter={(value: any) => [
                        `₹${Number(value).toLocaleString("en-IN")}`,
                        "Equity",
                    ]}
                />
                <Area
                    type="monotone"
                    dataKey="equity"
                    stroke={color}
                    strokeWidth={1.5}
                    fill="url(#eqGrad)"
                    dot={false}
                    activeDot={{ r: 3, strokeWidth: 0 }}
                />
            </AreaChart>
        </ResponsiveContainer>
    );
}
