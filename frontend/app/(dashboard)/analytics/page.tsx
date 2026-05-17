"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, ScatterChart, Scatter
} from "recharts";
import {
  TrendingUp, TrendingDown, Clock, Zap, Shield,
  Bot, BarChart3, Activity
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const TIME_RANGES = [
  { label: "7d", days: 7 },
  { label: "14d", days: 14 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
];

function MetricCard({
  title, value, unit, delta, icon: Icon, color = "blue"
}: {
  title: string; value: number | string; unit?: string;
  delta?: number; icon: React.ElementType; color?: string;
}) {
  const colorMap: Record<string, string> = {
    blue:   "text-nexus-blue   bg-nexus-blue/10",
    green:  "text-nexus-green  bg-nexus-green/10",
    amber:  "text-nexus-amber  bg-nexus-amber/10",
    red:    "text-nexus-red    bg-nexus-red/10",
    purple: "text-nexus-purple bg-nexus-purple/10",
  };
  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-muted-foreground uppercase tracking-wider">{title}</span>
        <div className={cn("p-2 rounded-lg", colorMap[color])}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <p className="text-3xl font-bold">
        {value}
        {unit && <span className="text-lg text-muted-foreground ml-1">{unit}</span>}
      </p>
      {delta !== undefined && (
        <div className={cn("flex items-center gap-1 text-xs mt-2",
          delta >= 0 ? "text-emerald-400" : "text-red-400")}>
          {delta >= 0
            ? <TrendingUp className="w-3 h-3" />
            : <TrendingDown className="w-3 h-3" />}
          {delta >= 0 ? "+" : ""}{delta}% vs prev period
        </div>
      )}
    </div>
  );
}

const TOOLTIP_STYLE = {
  contentStyle: {
    background: "hsl(222 47% 9%)",
    border: "1px solid hsl(222 47% 16%)",
    borderRadius: 8,
    fontSize: 12,
  }
};

export default function AnalyticsPage() {
  const [rangeDays, setRangeDays] = useState(14);

  const { data: overview } = useQuery({
    queryKey: ["analytics-overview"],
    queryFn: () => api.get("/analytics/overview").then(r => r.data),
    refetchInterval: 60_000,
  });
  const { data: trends } = useQuery({
    queryKey: ["pipeline-trends", rangeDays],
    queryFn: () => api.get(`/analytics/pipeline-trends?days=${rangeDays}`).then(r => r.data),
  });
  const { data: agentPerf } = useQuery({
    queryKey: ["agent-performance"],
    queryFn: () => api.get("/analytics/agent-performance").then(r => r.data),
  });
  const { data: riskDist } = useQuery({
    queryKey: ["risk-distribution"],
    queryFn: () => api.get("/analytics/risk-distribution").then(r => r.data),
  });

  const trendData = trends?.labels?.map((l: string, i: number) => ({
    day: l,
    success: trends.success[i],
    failed: trends.failed[i],
    duration: Math.round(trends.avg_duration_s?.[i] ?? 0),
    risk: trends.risk_scores?.[i] ?? 50,
  })) ?? [];

  const agentRadarData = (agentPerf?.agents ?? []).map((a: any) => ({
    agent: a.name.replace(" Agent", "").replace("NL ", "NL\n"),
    calls: a.calls_today,
    latency: Math.max(0, 5000 - a.avg_duration_ms) / 50,
    success: a.success_rate,
  }));

  const riskScatterData = Array.from({ length: 40 }, (_, i) => ({
    risk: Math.round(Math.random() * 100),
    duration: Math.round(100 + Math.random() * 400),
    name: `pipeline-${i}`,
  }));

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-sm text-muted-foreground">
            Engineering efficiency powered by AI insights
          </p>
        </div>

        {/* Time range selector */}
        <div className="flex items-center gap-1 bg-secondary rounded-lg p-1">
          {TIME_RANGES.map(({ label, days }) => (
            <button
              key={days}
              onClick={() => setRangeDays(days)}
              className={cn(
                "px-3 py-1.5 rounded-md text-sm transition-all",
                rangeDays === days
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Success Rate"
          value={overview?.success_rate ?? "--"}
          unit="%"
          delta={2.4}
          icon={TrendingUp}
          color="green"
        />
        <MetricCard
          title="Avg Pipeline Time"
          value={Math.round(overview?.avg_pipeline_duration_s ?? 0)}
          unit="s"
          delta={-18}
          icon={Clock}
          color="blue"
        />
        <MetricCard
          title="CI Time Saved"
          value={overview?.ci_time_saved_percent ?? "--"}
          unit="%"
          delta={8.1}
          icon={Zap}
          color="purple"
        />
        <MetricCard
          title="Avg Risk Score"
          value={overview?.avg_risk_score ?? "--"}
          unit="/100"
          delta={-5}
          icon={Shield}
          color="amber"
        />
      </div>

      {/* Pipeline success + duration trend */}
      <div className="glass rounded-xl p-5">
        <h3 className="text-sm font-medium mb-5">Pipeline Outcomes & Duration Trend</h3>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={trendData}>
            <defs>
              <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#10b981" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="fg" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 47% 16%)" />
            <XAxis dataKey="day" tick={{ fontSize: 11, fill: "hsl(215 20% 55%)" }} />
            <YAxis yAxisId="count" tick={{ fontSize: 11, fill: "hsl(215 20% 55%)" }} />
            <YAxis yAxisId="dur" orientation="right" tick={{ fontSize: 11, fill: "hsl(215 20% 55%)" }} />
            <Tooltip {...TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area yAxisId="count" type="monotone" dataKey="success" name="Success"  stroke="#10b981" fill="url(#sg)" strokeWidth={2} />
            <Area yAxisId="count" type="monotone" dataKey="failed"  name="Failed"   stroke="#ef4444" fill="url(#fg)" strokeWidth={2} />
            <Line  yAxisId="dur"   type="monotone" dataKey="duration" name="Avg Duration (s)" stroke="#8b5cf6" strokeWidth={2} dot={false} strokeDasharray="4 2" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Risk score trend + Agent radar */}
      <div className="grid grid-cols-2 gap-6">
        <div className="glass rounded-xl p-5">
          <h3 className="text-sm font-medium mb-5">Risk Score Trend</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 47% 16%)" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: "hsl(215 20% 55%)" }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "hsl(215 20% 55%)" }} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Line type="monotone" dataKey="risk" name="Risk Score" stroke="#f59e0b" strokeWidth={2.5} dot={{ fill: "#f59e0b", r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="glass rounded-xl p-5">
          <h3 className="text-sm font-medium mb-5">Agent Load Distribution</h3>
          <ResponsiveContainer width="100%" height={220}>
            <RadarChart data={agentRadarData}>
              <PolarGrid stroke="hsl(222 47% 16%)" />
              <PolarAngleAxis dataKey="agent" tick={{ fontSize: 10, fill: "hsl(215 20% 55%)" }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9, fill: "hsl(215 20% 55%)" }} />
              <Radar name="Calls" dataKey="calls" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.2} />
              <Radar name="Success %" dataKey="success" stroke="#10b981" fill="#10b981" fillOpacity={0.15} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Tooltip {...TOOLTIP_STYLE} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Agent performance table */}
      <div className="glass rounded-xl p-5">
        <div className="flex items-center gap-2 mb-5">
          <Bot className="w-4 h-4 text-nexus-purple" />
          <h3 className="text-sm font-medium">Agent Performance Breakdown</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-muted-foreground uppercase tracking-wider border-b border-border">
                <th className="text-left pb-3 pr-4">Agent</th>
                <th className="text-right pb-3 px-4">Calls Today</th>
                <th className="text-right pb-3 px-4">Avg Latency</th>
                <th className="text-right pb-3 px-4">Success Rate</th>
                <th className="pb-3 px-4">Performance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {(agentPerf?.agents ?? []).map((a: any) => (
                <tr key={a.name} className="hover:bg-secondary/30 transition-colors">
                  <td className="py-3 pr-4 font-medium">{a.name}</td>
                  <td className="py-3 px-4 text-right text-muted-foreground">{a.calls_today.toLocaleString()}</td>
                  <td className="py-3 px-4 text-right text-muted-foreground">{a.avg_duration_ms}ms</td>
                  <td className="py-3 px-4 text-right">
                    <span className={cn("font-medium", a.success_rate >= 99 ? "text-emerald-400" : "text-amber-400")}>
                      {a.success_rate}%
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-nexus-blue to-nexus-green"
                          style={{ width: `${a.success_rate}%` }}
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Risk vs Duration scatter */}
      <div className="glass rounded-xl p-5">
        <h3 className="text-sm font-medium mb-1">Risk Score vs Pipeline Duration</h3>
        <p className="text-xs text-muted-foreground mb-5">
          Correlation between change risk and time taken to validate
        </p>
        <ResponsiveContainer width="100%" height={240}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 47% 16%)" />
            <XAxis dataKey="risk"     name="Risk Score" label={{ value: "Risk Score", position: "insideBottom", offset: -5, fontSize: 11, fill: "hsl(215 20% 55%)" }} tick={{ fontSize: 11, fill: "hsl(215 20% 55%)" }} />
            <YAxis dataKey="duration" name="Duration (s)" label={{ value: "Duration (s)", angle: -90, position: "insideLeft", fontSize: 11, fill: "hsl(215 20% 55%)" }} tick={{ fontSize: 11, fill: "hsl(215 20% 55%)" }} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} {...TOOLTIP_STYLE} />
            <Scatter name="Pipelines" data={riskScatterData} fill="#8b5cf6" fillOpacity={0.7} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Risk distribution bar */}
      <div className="glass rounded-xl p-5">
        <h3 className="text-sm font-medium mb-5">Deployments by Risk Level</h3>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart
            data={riskDist ? Object.entries(riskDist.distribution).map(([name, value]) => ({ name, value })) : []}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 47% 16%)" />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: "hsl(215 20% 55%)" }} />
            <YAxis tick={{ fontSize: 11, fill: "hsl(215 20% 55%)" }} />
            <Tooltip {...TOOLTIP_STYLE} />
            <Bar dataKey="value" name="Pipelines" radius={[6, 6, 0, 0]}>
              {(riskDist ? Object.keys(riskDist.distribution) : []).map((key, i) => {
                const colors: Record<string, string> = { low: "#10b981", medium: "#f59e0b", high: "#f97316", critical: "#ef4444" };
                return <rect key={i} fill={colors[key] ?? "#8b5cf6"} />;
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
