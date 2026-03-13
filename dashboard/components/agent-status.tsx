"use client";

interface Props {
    regime: string;
    mode: string;
    prices: Record<string, number>;
}

const AGENTS = [
    "Regime Detector",
    "Momentum",
    "Mean Reversion",
    "Breakout",
    "Sentiment",
    "Contrarian",
    "Bull Aggregator",
    "Bear Aggregator",
    "Risk Guardian",
    "Orchestrator",
];

function modeBadgeClass(mode: string): string {
    const m = mode.toLowerCase();
    if (m.includes("aggressive")) return "badge-blue";
    if (m.includes("normal")) return "badge-green";
    if (m.includes("cautious")) return "badge-amber";
    if (m.includes("defensive") || m.includes("crisis")) return "badge-red";
    return "badge-gray";
}

function regimeBadgeClass(regime: string): string {
    const r = regime.toLowerCase();
    if (r.includes("bull")) return "badge-green";
    if (r.includes("bear")) return "badge-red";
    if (r.includes("mean")) return "badge-blue";
    if (r.includes("volatil") || r.includes("crisis")) return "badge-amber";
    return "badge-gray";
}

export function AgentStatus({ regime, mode }: Props) {
    return (
        <div className="card" style={{ display: "flex", flexDirection: "column" }}>
            <div
                style={{
                    fontSize: 13,
                    fontWeight: 500,
                    marginBottom: 16,
                    color: "var(--text-secondary)",
                }}
            >
                Agent Swarm
            </div>

            {/* Regime + Mode pills */}
            <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
                <span className={`badge ${regimeBadgeClass(regime)}`}>
                    {regime.replace(/_/g, " ") || "—"}
                </span>
                <span className={`badge ${modeBadgeClass(mode)}`}>
                    {mode.replace(/_/g, " ") || "—"}
                </span>
            </div>

            {/* Agent list */}
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {AGENTS.map((name) => (
                    <div
                        key={name}
                        style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "4px 0",
                        }}
                    >
                        <span
                            style={{
                                fontSize: 12,
                                color: "var(--text-primary)",
                                fontWeight: 450,
                            }}
                        >
                            {name}
                        </span>
                        <div
                            style={{
                                width: 6,
                                height: 6,
                                borderRadius: "50%",
                                background: "var(--green)",
                                opacity: 0.7,
                            }}
                        />
                    </div>
                ))}
            </div>
        </div>
    );
}
