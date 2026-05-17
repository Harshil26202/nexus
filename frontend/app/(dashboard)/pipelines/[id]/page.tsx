"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, GitBranch, Clock, Shield, CheckCircle2,
  XCircle, Zap, AlertTriangle, Bot, GitCommit,
  ChevronRight, Activity
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const RISK_COLORS: Record<string, string> = {
  low:      "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
  medium:   "text-amber-400   bg-amber-400/10   border-amber-400/30",
  high:     "text-orange-400  bg-orange-400/10  border-orange-400/30",
  critical: "text-red-400     bg-red-400/10     border-red-400/30",
};

function RiskGauge({ score }: { score: number }) {
  const color = score < 30 ? "#10b981" : score < 60 ? "#f59e0b" : score < 80 ? "#f97316" : "#ef4444";
  const angle = (score / 100) * 180 - 90;
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-32 h-16 overflow-hidden">
        <div className="absolute inset-0 rounded-t-full border-4 border-secondary" />
        <div
          className="absolute bottom-0 left-1/2 w-0.5 h-14 origin-bottom transition-transform duration-700"
          style={{
            background: color,
            transform: `translateX(-50%) rotate(${angle}deg)`,
          }}
        />
      </div>
      <p className="text-3xl font-bold mt-1" style={{ color }}>{score}</p>
      <p className="text-xs text-muted-foreground">/ 100 risk score</p>
    </div>
  );
}

function StageStep({ name, status, agentName, duration }: {
  name: string; status: string; agentName?: string; duration?: number;
}) {
  const isSuccess = status === "success" || status === "completed";
  const isFailed = status === "failed";
  const isRunning = status === "running";
  return (
    <div className="flex items-center gap-3">
      <div className={cn(
        "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
        isSuccess ? "bg-emerald-400/20" : isFailed ? "bg-red-400/20" : isRunning ? "bg-blue-400/20" : "bg-secondary"
      )}>
        {isSuccess ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> :
         isFailed  ? <XCircle      className="w-4 h-4 text-red-400" />     :
         isRunning ? <Activity     className="w-4 h-4 text-blue-400 animate-pulse" /> :
                     <div className="w-2 h-2 rounded-full bg-muted-foreground" />}
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium capitalize">{name.replace(/_/g, " ")}</p>
        {agentName && <p className="text-xs text-muted-foreground">via {agentName} agent</p>}
      </div>
      {duration && <span className="text-xs text-muted-foreground">{duration}s</span>}
    </div>
  );
}

export default function PipelineDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: pipeline, isLoading } = useQuery({
    queryKey: ["pipeline", id],
    queryFn: () => api.get(`/pipelines/${id}`).then(r => r.data),
    refetchInterval: p => (p?.status === "running" ? 3000 : false),
  });

  const { data: analysis } = useQuery({
    queryKey: ["pipeline-analysis", id],
    queryFn: () => api.get(`/pipelines/${id}/analysis`).then(r => r.data),
    enabled: !!id,
  });

  const { data: runs = [] } = useQuery({
    queryKey: ["pipeline-runs", id],
    queryFn: () => api.get(`/pipelines/${id}/runs`).then(r => r.data),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="p-8 space-y-4">
        <div className="h-8 w-48 skeleton rounded" />
        <div className="h-48 skeleton rounded-xl" />
        <div className="grid grid-cols-2 gap-4">
          <div className="h-64 skeleton rounded-xl" />
          <div className="h-64 skeleton rounded-xl" />
        </div>
      </div>
    );
  }

  if (!pipeline) return <div className="p-8 text-muted-foreground">Pipeline not found</div>;

  const riskClass = RISK_COLORS[pipeline.risk_level] ?? RISK_COLORS.medium;

  return (
    <div className="p-8 space-y-6">
      {/* Back nav */}
      <Link href="/pipelines" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit">
        <ArrowLeft className="w-4 h-4" />
        Back to Pipelines
      </Link>

      {/* Header card */}
      <div className="glass rounded-xl p-6 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold">{pipeline.repo_full_name}</h1>
            <div className="flex items-center gap-3 mt-2 text-sm text-muted-foreground">
              <div className="flex items-center gap-1">
                <GitBranch className="w-3.5 h-3.5" />
                {pipeline.branch}
              </div>
              <div className="flex items-center gap-1">
                <GitCommit className="w-3.5 h-3.5" />
                <code className="bg-secondary px-1.5 py-0.5 rounded text-nexus-purple text-xs">
                  {pipeline.commit_sha?.slice(0, 7)}
                </code>
              </div>
              {pipeline.pr_number && (
                <span className="bg-nexus-blue/10 text-nexus-blue text-xs px-2 py-0.5 rounded-full border border-nexus-blue/20">
                  PR #{pipeline.pr_number}
                </span>
              )}
            </div>
            <p className="text-sm mt-2 text-foreground">{pipeline.commit_message}</p>
          </div>
          {pipeline.risk_level && (
            <span className={cn("text-sm font-bold px-3 py-1.5 rounded-lg border", riskClass)}>
              {pipeline.risk_level.toUpperCase()} RISK
            </span>
          )}
        </div>

        {/* Status bar */}
        <div className="flex items-center gap-4 pt-2 border-t border-border">
          <div className="flex items-center gap-2">
            <span className={cn("status-dot", pipeline.status)} />
            <span className="text-sm capitalize font-medium">{pipeline.status}</span>
          </div>
          {pipeline.duration_seconds && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="w-3 h-3" />
              {pipeline.duration_seconds}s
            </div>
          )}
          {pipeline.author && (
            <span className="text-xs text-muted-foreground">by {pipeline.author}</span>
          )}
        </div>
      </div>

      {/* Main analysis grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left: Risk gauge + AI summary */}
        <div className="space-y-4">
          <div className="glass rounded-xl p-5 text-center">
            <h3 className="text-sm font-medium mb-4">Risk Assessment</h3>
            <RiskGauge score={Math.round(pipeline.risk_score ?? 0)} />
          </div>

          {analysis?.semantic_summary && (
            <div className="glass rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <Bot className="w-4 h-4 text-nexus-purple" />
                <span className="text-xs font-medium">AI Summary</span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {analysis.semantic_summary}
              </p>
            </div>
          )}

          {analysis?.ai_recommendation && (
            <div className="glass rounded-xl p-4 border border-nexus-blue/20">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-4 h-4 text-nexus-blue" />
                <span className="text-xs font-medium">Recommendation</span>
              </div>
              <p className="text-sm leading-relaxed">{analysis.ai_recommendation}</p>
            </div>
          )}
        </div>

        {/* Middle: Agent pipeline stages */}
        <div className="glass rounded-xl p-5">
          <h3 className="text-sm font-medium mb-5">Agent Pipeline</h3>
          <div className="space-y-5">
            {[
              { name: "semantic_analysis",  label: "Semantic Analysis", agent: "semantic_analyzer" },
              { name: "test_intelligence",  label: "Test Intelligence",  agent: "test_intelligence" },
              { name: "quality_gate",       label: "Quality Gate",       agent: "quality_gate"      },
              { name: "deployment_check",   label: "Deploy Decision",    agent: "orchestrator"      },
            ].map((s, i) => {
              const run = runs.find((r: any) => r.step_name === s.name);
              return (
                <div key={s.name}>
                  <StageStep
                    name={s.label}
                    status={run?.status ?? (i === 0 ? "completed" : "pending")}
                    agentName={s.agent}
                    duration={run?.duration_seconds}
                  />
                  {i < 3 && (
                    <div className="ml-4 w-0.5 h-4 bg-border mt-1" />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Blast radius + gate results */}
        <div className="space-y-4">
          {analysis?.blast_radius && (
            <div className="glass rounded-xl p-4">
              <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-nexus-amber" />
                Blast Radius
              </h3>
              {Object.entries(analysis.blast_radius as Record<string, string[]>).map(([key, values]) =>
                values.length > 0 ? (
                  <div key={key} className="mb-3">
                    <p className="text-xs text-muted-foreground capitalize mb-1.5">
                      {key.replace(/_/g, " ")}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {values.map((v: string) => (
                        <span key={v} className="text-xs bg-secondary px-2 py-0.5 rounded-full border border-border">
                          {v}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null
              )}
            </div>
          )}

          {analysis?.gate_results && (
            <div className="glass rounded-xl p-4">
              <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Shield className="w-4 h-4 text-nexus-blue" />
                Gate Results
              </h3>
              <div className="space-y-2">
                {(analysis.gate_results?.gates ?? []).map((g: any) => (
                  <div key={g.name} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground truncate">{g.name}</span>
                    <span className={cn(
                      "ml-2 px-2 py-0.5 rounded-full font-medium",
                      g.result === "pass" ? "text-emerald-400 bg-emerald-400/10" :
                      g.result === "warn" ? "text-amber-400 bg-amber-400/10" :
                                            "text-red-400 bg-red-400/10"
                    )}>
                      {g.result?.toUpperCase()}
                    </span>
                  </div>
                ))}
                <div className={cn(
                  "mt-3 p-2 rounded-lg text-xs font-medium text-center",
                  analysis.gate_results?.can_deploy
                    ? "bg-emerald-400/10 text-emerald-400"
                    : "bg-red-400/10 text-red-400"
                )}>
                  {analysis.gate_results?.can_deploy ? "APPROVED TO DEPLOY" : "DEPLOYMENT BLOCKED"}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Test selection */}
      {(analysis?.selected_tests?.length > 0 || analysis?.skipped_tests?.length > 0) && (
        <div className="glass rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium flex items-center gap-2">
              <Zap className="w-4 h-4 text-nexus-green" />
              Test Intelligence Selection
            </h3>
            {analysis?.skipped_tests?.length > 0 && (
              <span className="text-xs text-nexus-green bg-nexus-green/10 px-3 py-1 rounded-full border border-nexus-green/20">
                {analysis.skipped_tests.length} tests skipped · CI time saved
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted-foreground mb-2">Must Run ({analysis.selected_tests?.length ?? 0})</p>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {(analysis.selected_tests ?? []).slice(0, 20).map((t: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                    <span className="text-muted-foreground truncate">{t.name ?? t}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-2">Skipped ({analysis.skipped_tests?.length ?? 0})</p>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {(analysis.skipped_tests ?? []).slice(0, 20).map((t: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <div className="w-3 h-3 rounded-full border border-muted-foreground/30 flex-shrink-0" />
                    <span className="text-muted-foreground truncate opacity-60">{t.name ?? t}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
