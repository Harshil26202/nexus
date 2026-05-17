"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bot,
  GitBranch,
  LayoutDashboard,
  MessageSquare,
  Shield,
  Siren,
  BarChart3,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard",      label: "Dashboard",     icon: LayoutDashboard },
  { href: "/pipelines",      label: "Pipelines",     icon: GitBranch },
  { href: "/agents",         label: "Agent Monitor", icon: Bot },
  { href: "/quality-gates",  label: "Quality Gates", icon: Shield },
  { href: "/incidents",      label: "Incidents",     icon: Siren },
  { href: "/analytics",      label: "Analytics",     icon: BarChart3 },
  { href: "/chat",           label: "NL DevOps",     icon: MessageSquare },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 border-r border-border glass flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center gap-3 px-6 border-b border-border">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-nexus-blue to-nexus-purple flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-lg gradient-text">NEXUS</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                  active
                    ? "bg-primary/10 text-primary border border-primary/20 shadow-sm shadow-primary/10"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                )}
              >
                <Icon className={cn("w-4 h-4", active && "text-primary")} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Activity className="w-3 h-3 text-emerald-400" />
            <span>All systems operational</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Built on Azure AI Foundry
          </p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
