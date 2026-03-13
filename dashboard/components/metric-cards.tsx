"use client";

interface Props {
    loading: boolean;
    dailyPnl: number;
    capital: number;
    openPositions: number;
    regime: string;
    mode: string;
    winRate: number;
    totalTrades: number;
}

export function MetricCards({
    loading,
    dailyPnl,
    capital,
    openPositions,
    regime,
    mode,
    winRate,
    totalTrades,
}: Props) {
    const formatCurrency = (v: number) =>
        `₹${Math.abs(v).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

    const pnlColor = dailyPnl >= 0 ? "var(--green)" : "var(--red)";
    const pnlSign = dailyPnl >= 0 ? "+" : "-";
    const drawdown = capital > 0 ? ((dailyPnl < 0 ? Math.abs(dailyPnl) / capital : 0) * 100).toFixed(2) : "0.00";

    const cards = [
        {
            label: "Daily P&L",
            value: `${pnlSign}${formatCurrency(dailyPnl)}`,
            color: pnlColor,
            sub: `${((dailyPnl / capital) * 100).toFixed(2)}%`,
        },
        {
            label: "Capital",
            value: formatCurrency(capital + dailyPnl),
            color: "var(--text-primary)",
            sub: `Base: ${formatCurrency(capital)}`,
        },
        {
            label: "Open Positions",
            value: String(openPositions),
            color: "var(--text-primary)",
            sub: `Max: 3`,
        },
        {
            label: "Drawdown",
            value: `${drawdown}%`,
            color: parseFloat(drawdown) > 2 ? "var(--red)" : "var(--text-primary)",
            sub: `Limit: 3.00%`,
        },
        {
            label: "Win Rate",
            value: totalTrades > 0 ? `${winRate.toFixed(0)}%` : "—",
            color: "var(--text-primary)",
            sub: `${totalTrades} trades`,
        },
        {
            label: "Regime / Mode",
            value: regime.replace(/_/g, " "),
            color: "var(--text-primary)",
            sub: mode.replace(/_/g, " "),
            small: true,
        },
    ];

    return (
        <div
            style={{
                display: "grid",
                gridTemplateColumns: "repeat(6, 1fr)",
                gap: 12,
            }}
        >
            {cards.map((c) => (
                <div key={c.label} className="card card-compact">
                    <div className="metric-label">{c.label}</div>
                    {loading ? (
                        <div className="skeleton" style={{ height: 28, width: "70%" }} />
                    ) : (
                        <>
                            <div
                                className="metric-value"
                                style={{
                                    color: c.color,
                                    fontSize: c.small ? "0.875rem" : undefined,
                                    textTransform: c.small ? "capitalize" : undefined,
                                }}
                            >
                                {c.value}
                            </div>
                            <div
                                style={{
                                    fontSize: 11,
                                    color: "var(--text-muted)",
                                    marginTop: 2,
                                    textTransform: "capitalize",
                                }}
                            >
                                {c.sub}
                            </div>
                        </>
                    )}
                </div>
            ))}
        </div>
    );
}
