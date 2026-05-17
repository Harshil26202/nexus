"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  GitBranch, Clock, AlertTriangle, CheckCircle2, XCircle,
  RotateCcw, ArrowUpRight, Filter, Search
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_CONFIG = {
  success:   { icon: CheckCircle2, color: "text-emerald-400", bg: "bg-emerald-400/10", dot: "success" },
  failed:    { icon: XCircle,      color: "text-red-400",     bg: "bg-red-400/10",     dot: "failed" },
  running:   { icon: RotateCcw,    color: "text-blue-400",    bg: "bg-blue-400/10",    dot: "running" },
  pending:   { icon: Clock,        color: "text-muted-foreground", bg: "bg-muted",      dot: "pending" },
  cancelled: { icon: XCircle,      color: "text-muted-foreground", bg: "bg-muted",      dot: "pending" },
};

const RISK_CONFIG = {
  low:      "risk-low",
  medium:   "risk-medium",
  high:     "risk-high",
  critical: "risk-critical",
};

function PipelineRow({ p }: { p: any }) {
  const status = STATUS_CONFIG[p.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.pending;
  const Icon = status.icon;
  return (
    <Link href={`/pipelines/${p.id}`}>
      <div className="flex items-center gap-4 p-4 rounded-xl glass hover:bg-secondary/50 transition-all border border-transparent hover:border-border cursor-pointer group">
        {/* Status */}
        <div className={cn("p-2 rounded-lg", status.bg)}>
          <Icon className={cn("w-4 h-4", status.color, p.status === "running" && "animate-spin")} />
        </div>

        {/* Repo + commit */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm truncate">{p.repo_full_name}</span>
            {p.pr_number && (
              <span className="text-xs text-nexus-blue bg-nexus-blue/10 px-2 py-0.5 rounded-full border border-nexus-blue/20">
                PR #{p.pr_number}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1">
            <GitBranch className="w-3 h-3 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">{p.branch}</span>
            <code className="text-xs text-nexus-purple bg-nexus-purple/10 px-1.5 py-0.5 rounded">
              {p.commit_sha?.slice(0, 7)}
            </code>
          </div>
        </div>

        {/* Commit message */}
        <p className="text-sm text-muted-foreground truncate max-w-xs hidden lg:block">
          {p.commit_message}
        </p>

        {/* Risk */}
        {p.risk_level && (
          <span className={cn("text-xs px-2 py-1 rounded-full font-medium", RISK_CONFIG[p.risk_level as keyof typeof RISK_CONFIG])}>
            {p.risk_level}
          </span>
        )}
        {p.risk_score !== null && (
          <span className="text-xs text-muted-foreground w-12 text-right">
            {Math.round(p.risk_score)}
          </span>
        )}

        {/* Duration */}
        <span className="text-xs text-muted-foreground w-20 text-right hidden md:block">
          {p.duration_seconds ? `${p.duration_seconds}s` : "--"}
        </span>

        {/* Time */}
        <span className="text-xs text-muted-foreground w-24 text-right">
          {p.created_at ? formatDistanceToNow(new Date(p.created_at), { addSuffix: true }) : "--"}
        </span>

        <ArrowUpRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </Link>
  );
}

export default function PipelinesPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const { data: pipelines = [], isLoading } = useQuery({
    queryKey: ["pipelines", statusFilter],
    queryFn: () =>
      api.get(`/pipelines?limit=50${statusFilter ? `&status=${statusFilter}` : ""}`).then(r => r.data),
    refetchInterval: 10_000,
  });

  const filtered = search
    ? pipelines.filter((p: any) =>
        p.repo_full_name?.includes(search) ||
        p.commit_sha?.includes(search) ||
        p.commit_message?.toLowerCase().includes(search.toLowerCase())
      )
    : pipelines;

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Pipelines</h1>
          <p className="text-sm text-muted-foreground">AI-analyzed delivery pipeline runs</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search repo, SHA, message..."
            className="w-full bg-secondary border border-border rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <div className="flex items-center gap-2">
          {["", "running", "success", "failed"].map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={cn(
                "text-xs px-3 py-1.5 rounded-full border transition-all",
                statusFilter === s
                  ? "bg-primary/10 text-primary border-primary/30"
                  : "text-muted-foreground border-border hover:border-muted-foreground"
              )}
            >
              {s || "All"}
            </button>
          ))}
        </div>
      </div>

      {/* Table header */}
      <div className="flex items-center gap-4 px-4 text-xs text-muted-foreground uppercase tracking-wider">
        <div className="w-10" />
        <div className="flex-1">Repository</div>
        <div className="max-w-xs hidden lg:block">Message</div>
        <div className="w-20">Risk</div>
        <div className="w-12">Score</div>
        <div className="w-20 hidden md:block">Duration</div>
        <div className="w-24">When</div>
        <div className="w-4" />
      </div>

      {/* Rows */}
      <div className="space-y-2">
        {isLoading
          ? Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-16 skeleton rounded-xl" />
            ))
          : filtered.map((p: any) => <PipelineRow key={p.id} p={p} />)}
        {!isLoading && filtered.length === 0 && (
          <div className="text-center py-16 text-muted-foreground">
            No pipelines found
          </div>
        )}
      </div>
    </div>
  );
}
