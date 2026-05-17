"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, Zap, Clock, CheckCircle2, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const AGENT_META: Record<string, { color: string; description: string }> = {
  orchestrator:      { color: "nexus-blue",   description: "Master coordinator — routes events to specialized agents" },
  semantic_analyzer: { color: "nexus-purple", description: "Understands what code changes mean, not just what lines changed" },
  test_intelligence: { color: "nexus-green",  description: "Selects optimal test suite, skips low-signal tests, generates missing tests" },
  quality_gate:      { color: "nexus-amber",  description: "Adaptive go/no-go decisions using context-aware thresholds" },
  incident_response: { color: "nexus-red",    description: "Root cause analysis, postmortem generation, fix suggestions" },
  monitoring:        { color: "nexus-blue",   description: "Post-deploy health watching, anomaly detection, auto-rollback triggers" },
  nl_devops:         { color: "nexus-purple", description: "Natural language interface for all DevOps operations" },
};

function AgentCard({ agent }: { agent: any }) {
  const meta = AGENT_META[agent.name] ?? { color: "nexus-blue", description: "" };
  const isActive = agent.status === "active";

  return (
    <div className="glass rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center", `bg-${meta.color}/10`)}>
            <Bot className={cn("w-5 h-5", `text-${meta.color}`)} />
          </div>
          <div>
            <p className="font-medium text-sm capitalize">{agent.name.replace(/_/g, " ")}</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className={cn("status-dot", isActive ? "running" : "pending")} />
              <span className={cn("text-xs", isActive ? "text-blue-400" : "text-muted-foreground")}>
                {isActive ? `${agent.tasks_running} task${agent.tasks_running !== 1 ? "s" : ""} running` : "idle"}
              </span>
            </div>
          </div>
        </div>
        {isActive && (
          <div className="w-2 h-2 rounded-full bg-nexus-blue animate-pulse-glow" />
        )}
      </div>

      <p className="text-xs text-muted-foreground leading-relaxed">{meta.description}</p>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-secondary rounded-lg p-2 text-center">
          <p className="text-xs text-muted-foreground">Today's calls</p>
          <p className="font-bold text-sm">{agent.calls_today ?? "--"}</p>
        </div>
        <div className="bg-secondary rounded-lg p-2 text-center">
          <p className="text-xs text-muted-foreground">Avg latency</p>
          <p className="font-bold text-sm">{agent.avg_duration_ms ? `${agent.avg_duration_ms}ms` : "--"}</p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">Success rate</span>
        <div className="flex items-center gap-2">
          <div className="w-24 h-1.5 bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-400 rounded-full"
              style={{ width: `${agent.success_rate ?? 100}%` }}
            />
          </div>
          <span className="text-xs font-medium text-emerald-400">{agent.success_rate ?? "--"}%</span>
        </div>
      </div>
    </div>
  );
}

export default function AgentsPage() {
  const { data: stats } = useQuery({
    queryKey: ["agent-stats"],
    queryFn: () => api.get("/agents/stats/summary").then(r => r.data),
    refetchInterval: 5_000,
  });
  const { data: perf } = useQuery({
    queryKey: ["agent-performance"],
    queryFn: () => api.get("/analytics/agent-performance").then(r => r.data),
  });

  const agents = (stats?.agents ?? []).map((a: any) => {
    const perfData = (perf?.agents ?? []).find((p: any) => p.name.toLowerCase().includes(a.name.split("_")[0]));
    return { ...a, ...perfData };
  });

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Agent Monitor</h1>
        <p className="text-sm text-muted-foreground">Real-time status of all NEXUS AI agents</p>
      </div>

      {/* Summary bar */}
      <div className="flex items-center gap-6 glass rounded-xl p-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-nexus-blue animate-pulse" />
          <span className="text-sm">{stats?.active_agents ?? "--"} active agents</span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">{stats?.queued_tasks ?? "--"} tasks queued</span>
        </div>
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span className="text-sm text-muted-foreground">{stats?.completed_today ?? "--"} completed today</span>
        </div>
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-nexus-amber" />
          <span className="text-sm text-muted-foreground">
            {stats?.total_tokens_today?.toLocaleString() ?? "--"} tokens used
          </span>
        </div>
      </div>

      {/* Agent grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {agents.length > 0
          ? agents.map((a: any) => <AgentCard key={a.name} agent={a} />)
          : Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="h-52 skeleton rounded-xl" />
            ))
        }
      </div>

      {/* Model info */}
      <div className="glass rounded-xl p-5">
        <h3 className="text-sm font-medium mb-3">Model Configuration</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          {[
            { label: "Primary Model", value: "GPT-4o", sub: "Azure AI Foundry" },
            { label: "Fast Inference", value: "GPT-4o-mini", sub: "Classification tasks" },
            { label: "Embeddings", value: "text-embedding-3-large", sub: "Vector search" },
            { label: "Vector Store", value: "Azure AI Search", sub: "Hybrid retrieval" },
          ].map(({ label, value, sub }) => (
            <div key={label} className="bg-secondary rounded-lg p-3">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="font-medium mt-1">{value}</p>
              <p className="text-xs text-muted-foreground">{sub}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
