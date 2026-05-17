"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell
} from "recharts";
import {
  GitBranch, Zap, Shield, Siren, TrendingUp, Clock,
  CheckCircle2, XCircle, AlertTriangle, Activity, Bot
} from "lucide-react";
import { api } from "@/lib/api";
import { LivePipelineStream } from "@/components/dashboard/live-pipeline-stream";
import { AgentStatusGrid } from "@/components/dashboard/agent-status-grid";

const RISK_COLORS = { low: "#10b981", medium: "#f59e0b", high: "#f97316", critical: "#ef4444" };

function StatCard({
  title, value, sub, icon: Icon, trend, color = "blue"
}: {
  title: string; value: string | number; sub?: string;
  icon: React.ElementType; trend?: number; color?: string;
}) {
  const colorMap: Record<string, string> = {
    blue: "text-nexus-blue bg-nexus-blue/10",
    green: "text-nexus-green bg-nexus-green/10",
    amber: "text-nexus-amber bg-nexus-amber/10",
    red: "text-nexus-red bg-nexus-red/10",
    purple: "text-nexus-purple bg-nexus-purple/10",
  };
  return (
    <div className="glass rounded-xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{title}</span>
        <div className={`p-2 rounded-lg ${colorMap[color]}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div>
        <p className="text-3xl font-bold">{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </div>
      {trend !== undefined && (
        <div className={`flex items-center gap-1 text-xs ${trend >= 0 ? "text-emerald-400" : "text-red-400"}`}>
          <TrendingUp className="w-3 h-3" />
          {trend >= 0 ? "+" : ""}{trend}% vs last week
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { data: overview } = useQuery({
    queryKey: ["analytics-overview"],
    queryFn: () => api.get("/analytics/overview").then(r => r.data),
    refetchInterval: 30_000,
  });
  const { data: trends } = useQuery({
    queryKey: ["pipeline-trends"],
    queryFn: () => api.get("/analytics/pipeline-trends?days=14").then(r => r.data),
  });
  const { data: riskDist } = useQuery({
    queryKey: ["risk-distribution"],
    queryFn: () => api.get("/analytics/risk-distribution").then(r => r.data),
  });
  const { data: agentPerf } = useQuery({
    queryKey: ["agent-performance"],
    queryFn: () => api.get("/analytics/agent-performance").then(r => r.data),
  });

  const riskPieData = riskDist
    ? Object.entries(riskDist.distribution).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Engineering Intelligence</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Real-time AI-powered view of your delivery pipeline
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-400/10 px-3 py-1.5 rounded-full border border-emerald-400/20">
          <span className="status-dot success" />
          7 agents active
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Pipeline Success Rate"
          value={`${overview?.success_rate ?? "--"}%`}
          icon={CheckCircle2}
          trend={2.4}
          color="green"
          sub={`${overview?.total_pipelines ?? "--"} total pipelines`}
        />
        <StatCard
          title="CI Time Saved"
          value={`${overview?.ci_time_saved_percent ?? "--"}%`}
          icon={Zap}
          trend={8.1}
          color="blue"
          sub="via Test Intelligence"
        />
        <StatCard
          title="Open Incidents"
          value={overview?.open_incidents ?? "--"}
          icon={Siren}
          color="red"
          sub={`Avg MTTR: ${overview?.mttr_minutes ?? "--"}m`}
        />
        <StatCard
          title="Deploys Blocked"
          value={overview?.deployments_blocked ?? "--"}
          icon={Shield}
          color="amber"
          sub="by AI Quality Gates"
          trend={-15}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Pipeline trend */}
        <div className="col-span-2 glass rounded-xl p-5">
          <h3 className="text-sm font-medium mb-4">Pipeline Trends (14 days)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={trends?.labels?.map((l: string, i: number) => ({
              day: l,
              success: trends.success[i],
              failed: trends.failed[i],
            })) ?? []}>
              <defs>
                <linearGradient id="successGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="failedGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 47% 16%)" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: "hsl(215 20% 55%)" }} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(215 20% 55%)" }} />
              <Tooltip
                contentStyle={{ background: "hsl(222 47% 9%)", border: "1px solid hsl(222 47% 16%)", borderRadius: 8 }}
              />
              <Area type="monotone" dataKey="success" stroke="#10b981" fill="url(#successGrad)" strokeWidth={2} />
              <Area type="monotone" dataKey="failed"  stroke="#ef4444" fill="url(#failedGrad)"  strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Risk distribution */}
        <div className="glass rounded-xl p-5">
          <h3 className="text-sm font-medium mb-4">Risk Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={riskPieData}
                cx="50%" cy="50%"
                innerRadius={50} outerRadius={80}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {riskPieData.map((entry, i) => (
                  <Cell key={i} fill={RISK_COLORS[entry.name as keyof typeof RISK_COLORS] ?? "#8b5cf6"} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "hsl(222 47% 9%)", border: "1px solid hsl(222 47% 16%)", borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Agent performance */}
      <div className="glass rounded-xl p-5">
        <h3 className="text-sm font-medium mb-4">Agent Performance Today</h3>
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={agentPerf?.agents ?? []}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 47% 16%)" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: "hsl(215 20% 55%)" }} />
            <YAxis tick={{ fontSize: 11, fill: "hsl(215 20% 55%)" }} />
            <Tooltip contentStyle={{ background: "hsl(222 47% 9%)", border: "1px solid hsl(222 47% 16%)", borderRadius: 8 }} />
            <Bar dataKey="calls_today" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Live feed */}
      <div className="grid grid-cols-2 gap-6">
        <div className="glass rounded-xl p-5">
          <h3 className="text-sm font-medium mb-4 flex items-center gap-2">
            <span className="status-dot running" />
            Live Pipeline Events
          </h3>
          <LivePipelineStream />
        </div>
        <div className="glass rounded-xl p-5">
          <h3 className="text-sm font-medium mb-4 flex items-center gap-2">
            <Bot className="w-4 h-4 text-nexus-purple" />
            Agent Activity
          </h3>
          <AgentStatusGrid />
        </div>
      </div>
    </div>
  );
}
