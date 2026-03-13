"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    ArrowLeftRight,
    ClipboardList,
    Activity,
} from "lucide-react";

const NAV = [
    { href: "/", label: "Overview", icon: LayoutDashboard },
    { href: "/trades", label: "Trades", icon: ArrowLeftRight },
    { href: "/orders", label: "Orders", icon: ClipboardList },
    { href: "/agents", label: "Agents", icon: Activity },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <aside
            style={{
                width: 200,
                borderRight: "1px solid var(--border)",
                padding: "24px 12px",
                display: "flex",
                flexDirection: "column",
                gap: 4,
                flexShrink: 0,
            }}
        >
            {/* Logo */}
            <div
                style={{
                    padding: "0 12px",
                    marginBottom: 24,
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                }}
            >
                <div
                    style={{
                        width: 24,
                        height: 24,
                        borderRadius: 6,
                        background: "#111827",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#fff",
                        fontSize: 11,
                        fontWeight: 700,
                    }}
                >
                    H
                </div>
                <span
                    style={{
                        fontSize: 14,
                        fontWeight: 600,
                        color: "var(--text-primary)",
                        letterSpacing: "-0.01em",
                    }}
                >
                    HYDRA
                </span>
            </div>

            {/* Nav items */}
            <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {NAV.map((item) => {
                    const active = pathname === item.href;
                    const Icon = item.icon;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`nav-link ${active ? "nav-link-active" : ""}`}
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                            }}
                        >
                            <Icon size={15} strokeWidth={1.8} />
                            {item.label}
                        </Link>
                    );
                })}
            </nav>

            {/* Bottom */}
            <div style={{ marginTop: "auto", padding: "0 12px" }}>
                <p
                    style={{
                        fontSize: 10,
                        color: "var(--text-muted)",
                        lineHeight: 1.5,
                    }}
                >
                    HYDRA-Lite v1.0
                    <br />
                    Paper Trading
                </p>
            </div>
        </aside>
    );
}
