"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Siren, AlertTriangle, CheckCircle2, Clock, GitCommit,
  MessageSquare, ExternalLink, ChevronDown, ChevronRight
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const SEV_CONFIG = {
  sev1: { label: "SEV1", color: "text-red-400 bg-red-400/10 border-red-400/30" },
  sev2: { label: "SEV2", color: "text-orange-400 bg-orange-400/10 border-orange-400/30" },
  sev3: { label: "SEV3", color: "text-amber-400 bg-amber-400/10 border-amber-400/30" },
  sev4: { label: "SEV4", color: "text-muted-foreground bg-secondary border-border" },
};

const STATUS_CONFIG = {
  open:          { label: "Open",         color: "text-red-400",     dot: "failed" },
  investigating: { label: "Investigating", color: "text-amber-400",   dot: "running" },
  identified:    { label: "Identified",   color: "text-blue-400",    dot: "running" },
  monitoring:    { label: "Monitoring",   color: "text-nexus-purple", dot: "running" },
  resolved:      { label: "Resolved",     color: "text-emerald-400", dot: "success" },
};

function IncidentRow({ inc }: { inc: any }) {
  const [expanded, setExpanded] = useState(false);
  const sev = SEV_CONFIG[inc.severity as keyof typeof SEV_CONFIG] ?? SEV_CONFIG.sev4;
  const status = STATUS_CONFIG[inc.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.open;

  return (
    <div className="glass rounded-xl border border-border overflow-hidden">
      <div
        className="flex items-center gap-4 p-4 cursor-pointer hover:bg-secondary/30 transition-colors"
        onClick={() => setExpanded(v => !v)}
      >
        <span className={cn("text-xs font-bold px-2 py-1 rounded border", sev.color)}>
          {sev.label}
        </span>

        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{inc.title}</p>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs text-muted-foreground">{inc.service}</span>
            <span className="text-xs text-muted-foreground">·</span>
            <span className="text-xs text-muted-foreground">{inc.environment}</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <span className={cn("status-dot", status.dot)} />
          <span className={cn("text-xs", status.color)}>{status.label}</span>
        </div>

        {inc.mttr_seconds && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="w-3 h-3" />
            {Math.round(inc.mttr_seconds / 60)}m MTTR
          </div>
        )}

        <span className="text-xs text-muted-foreground w-24 text-right">
          {inc.created_at ? formatDistanceToNow(new Date(inc.created_at), { addSuffix: true }) : "--"}
        </span>

        {expanded ? <ChevronDown className="w-4 h-4 text-muted-foreground" /> : <ChevronRight className="w-4 h-4 text-muted-foreground" />}
      </div>

      {expanded && (
        <div className="border-t border-border p-5 space-y-4 bg-secondary/20">
          {inc.root_cause_commit && (
            <div className="flex items-center gap-2">
              <GitCommit className="w-4 h-4 text-nexus-purple" />
              <span className="text-sm text-muted-foreground">Root cause commit:</span>
              <code className="text-xs bg-nexus-purple/10 text-nexus-purple px-2 py-0.5 rounded">
                {inc.root_cause_commit?.slice(0, 7)}
              </code>
            </div>
          )}
          {inc.root_cause_analysis && (
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">Root Cause Analysis</p>
              <p className="text-sm text-foreground leading-relaxed">{inc.root_cause_analysis}</p>
            </div>
          )}
          {inc.slack_summary && (
            <div className="flex items-start gap-2 bg-secondary rounded-lg p-3">
              <MessageSquare className="w-4 h-4 text-nexus-green mt-0.5" />
              <p className="text-sm">{inc.slack_summary}</p>
            </div>
          )}
          <div className="flex gap-3">
            {inc.pagerduty_id && (
              <a href="#" className="text-xs flex items-center gap-1 text-nexus-green hover:underline">
                <ExternalLink className="w-3 h-3" /> PagerDuty
              </a>
            )}
            {inc.github_issue_url && (
              <a href={inc.github_issue_url} className="text-xs flex items-center gap-1 text-nexus-blue hover:underline">
                <ExternalLink className="w-3 h-3" /> GitHub Issue
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function IncidentsPage() {
  const [statusFilter, setStatusFilter] = useState("");

  const { data: incidents = [], isLoading } = useQuery({
    queryKey: ["incidents", statusFilter],
    queryFn: () =>
      api.get(`/incidents?limit=50${statusFilter ? `&status=${statusFilter}` : ""}`).then(r => r.data),
    refetchInterval: 15_000,
  });

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Incidents</h1>
          <p className="text-sm text-muted-foreground">AI-powered root cause analysis and postmortem generation</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2">
        {["", "open", "investigating", "identified", "resolved"].map(s => (
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

      <div className="space-y-3">
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-20 skeleton rounded-xl" />)
          : incidents.map((inc: any) => <IncidentRow key={inc.id} inc={inc} />)}
        {!isLoading && incidents.length === 0 && (
          <div className="text-center py-20 text-muted-foreground">
            <CheckCircle2 className="w-12 h-12 mx-auto mb-3 text-emerald-400 opacity-50" />
            No incidents — all systems clear
          </div>
        )}
      </div>
    </div>
  );
}
