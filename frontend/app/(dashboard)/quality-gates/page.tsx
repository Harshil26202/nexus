"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Shield, Plus, ToggleLeft, ToggleRight, Trash2,
  Brain, AlertTriangle, ChevronDown, ChevronRight, Zap
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import toast from "react-hot-toast";

const GATE_TYPES = [
  { value: "coverage",    label: "Code Coverage",    icon: "🧪", desc: "Minimum test coverage threshold" },
  { value: "security",    label: "Security Scan",    icon: "🔒", desc: "CVE and SAST vulnerability gates" },
  { value: "performance", label: "Performance",      icon: "⚡", desc: "Latency and throughput regression detection" },
  { value: "complexity",  label: "Code Complexity",  icon: "🧩", desc: "Cyclomatic complexity ceiling" },
  { value: "custom_ai",   label: "AI Custom Gate",   icon: "🤖", desc: "Free-form AI-evaluated gate with natural language criteria" },
];

const GATE_TYPE_COLORS: Record<string, string> = {
  coverage:    "text-nexus-green  bg-nexus-green/10  border-nexus-green/20",
  security:    "text-nexus-red    bg-nexus-red/10    border-nexus-red/20",
  performance: "text-nexus-blue   bg-nexus-blue/10   border-nexus-blue/20",
  complexity:  "text-nexus-amber  bg-nexus-amber/10  border-nexus-amber/20",
  custom_ai:   "text-nexus-purple bg-nexus-purple/10 border-nexus-purple/20",
};

function CreateGateModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    gate_type: "coverage",
    repo_pattern: "*",
    threshold_value: "",
    threshold_operator: "gte",
    adaptive_enabled: true,
    adaptive_prompt: "",
    description: "",
  });

  const { mutate, isPending } = useMutation({
    mutationFn: (data: typeof form) => api.post("/quality-gates", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["quality-gates"] });
      toast.success("Gate created");
      onClose();
    },
    onError: () => toast.error("Failed to create gate"),
  });

  const selectedType = GATE_TYPES.find(t => t.value === form.gate_type);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass rounded-2xl w-full max-w-lg border border-border shadow-2xl">
        <div className="p-6 border-b border-border">
          <h2 className="font-bold text-lg">Create Quality Gate</h2>
          <p className="text-sm text-muted-foreground mt-1">
            AI-adaptive gates adjust thresholds based on context
          </p>
        </div>

        <div className="p-6 space-y-5">
          {/* Gate type */}
          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider block mb-2">Gate Type</label>
            <div className="grid grid-cols-2 gap-2">
              {GATE_TYPES.map(t => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setForm(f => ({ ...f, gate_type: t.value }))}
                  className={cn(
                    "flex items-center gap-2 p-3 rounded-lg border text-sm transition-all text-left",
                    form.gate_type === t.value
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border bg-secondary text-muted-foreground hover:border-muted-foreground"
                  )}
                >
                  <span>{t.icon}</span>
                  <span>{t.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Name */}
          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider block mb-2">Gate Name</label>
            <input
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder={`e.g. ${selectedType?.label} — Production`}
              className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Repo pattern */}
          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider block mb-2">
              Repo Pattern
              <span className="normal-case ml-2 text-muted-foreground font-normal">glob, e.g. org/service-*</span>
            </label>
            <input
              value={form.repo_pattern}
              onChange={e => setForm(f => ({ ...f, repo_pattern: e.target.value }))}
              placeholder="* (all repos)"
              className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Threshold — skip for custom_ai */}
          {form.gate_type !== "custom_ai" && (
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="text-xs text-muted-foreground uppercase tracking-wider block mb-2">Threshold</label>
                <input
                  type="number"
                  value={form.threshold_value}
                  onChange={e => setForm(f => ({ ...f, threshold_value: e.target.value }))}
                  placeholder={form.gate_type === "coverage" ? "80" : "0"}
                  className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div className="w-32">
                <label className="text-xs text-muted-foreground uppercase tracking-wider block mb-2">Operator</label>
                <select
                  value={form.threshold_operator}
                  onChange={e => setForm(f => ({ ...f, threshold_operator: e.target.value }))}
                  className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="gte">≥ (at least)</option>
                  <option value="lte">≤ (at most)</option>
                  <option value="eq">= (exactly)</option>
                </select>
              </div>
            </div>
          )}

          {/* AI adaptive */}
          <div className="bg-nexus-purple/5 border border-nexus-purple/20 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-nexus-purple" />
                <span className="text-sm font-medium">AI Adaptive Mode</span>
              </div>
              <button
                type="button"
                onClick={() => setForm(f => ({ ...f, adaptive_enabled: !f.adaptive_enabled }))}
              >
                {form.adaptive_enabled
                  ? <ToggleRight className="w-6 h-6 text-nexus-purple" />
                  : <ToggleLeft className="w-6 h-6 text-muted-foreground" />}
              </button>
            </div>
            {form.adaptive_enabled && (
              <textarea
                value={form.adaptive_prompt}
                onChange={e => setForm(f => ({ ...f, adaptive_prompt: e.target.value }))}
                placeholder="Describe how the AI should adapt this gate. e.g. 'Be stricter on Friday deploys, relax for hotfixes tagged #skip-gate'"
                rows={3}
                className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
              />
            )}
          </div>

          {/* Custom AI prompt */}
          {form.gate_type === "custom_ai" && (
            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-wider block mb-2">AI Gate Criteria</label>
              <textarea
                value={form.adaptive_prompt}
                onChange={e => setForm(f => ({ ...f, adaptive_prompt: e.target.value }))}
                placeholder="e.g. 'Block deployment if the diff touches auth middleware without a corresponding security review comment in the PR'"
                rows={4}
                className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
              />
            </div>
          )}
        </div>

        <div className="p-6 border-t border-border flex gap-3 justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-secondary transition-all"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!form.name || isPending}
            onClick={() => mutate(form)}
            className="px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-40 transition-all flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            {isPending ? "Creating..." : "Create Gate"}
          </button>
        </div>
      </div>
    </div>
  );
}

function GateCard({ gate }: { gate: any }) {
  const [expanded, setExpanded] = useState(false);
  const qc = useQueryClient();
  const typeColor = GATE_TYPE_COLORS[gate.gate_type] ?? GATE_TYPE_COLORS.coverage;
  const typeMeta = GATE_TYPES.find(t => t.value === gate.gate_type);

  const toggle = useMutation({
    mutationFn: () => api.patch(`/quality-gates/${gate.id}/toggle`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["quality-gates"] }),
  });

  const del = useMutation({
    mutationFn: () => api.delete(`/quality-gates/${gate.id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["quality-gates"] });
      toast.success("Gate deleted");
    },
  });

  return (
    <div className={cn("glass rounded-xl border overflow-hidden transition-all", gate.enabled ? "border-border" : "border-border opacity-60")}>
      <div
        className="flex items-center gap-4 p-4 cursor-pointer hover:bg-secondary/30"
        onClick={() => setExpanded(v => !v)}
      >
        {/* Type badge */}
        <span className={cn("text-xs font-medium px-2.5 py-1 rounded-full border", typeColor)}>
          {typeMeta?.icon} {typeMeta?.label}
        </span>

        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm">{gate.name}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Applies to: <code className="bg-secondary px-1 rounded">{gate.repo_pattern}</code>
          </p>
        </div>

        {/* Threshold */}
        {gate.threshold_value !== null && gate.threshold_value !== undefined && (
          <div className="text-center hidden md:block">
            <p className="text-xs text-muted-foreground">Threshold</p>
            <p className="font-bold text-sm">
              {gate.threshold_operator === "gte" ? "≥" : gate.threshold_operator === "lte" ? "≤" : "="}{" "}
              {gate.threshold_value}
            </p>
          </div>
        )}

        {/* Adaptive badge */}
        {gate.adaptive_enabled && (
          <div className="flex items-center gap-1 text-xs text-nexus-purple bg-nexus-purple/10 px-2 py-1 rounded-full border border-nexus-purple/20">
            <Brain className="w-3 h-3" />
            AI Adaptive
          </div>
        )}

        {/* Controls */}
        <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
          <button
            onClick={() => toggle.mutate()}
            title={gate.enabled ? "Disable" : "Enable"}
            className="p-1.5 rounded-lg hover:bg-secondary transition-all"
          >
            {gate.enabled
              ? <ToggleRight className="w-5 h-5 text-emerald-400" />
              : <ToggleLeft className="w-5 h-5 text-muted-foreground" />}
          </button>
          <button
            onClick={() => {
              if (confirm("Delete this gate?")) del.mutate();
            }}
            className="p-1.5 rounded-lg hover:bg-red-400/10 text-muted-foreground hover:text-red-400 transition-all"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        {expanded ? <ChevronDown className="w-4 h-4 text-muted-foreground" /> : <ChevronRight className="w-4 h-4 text-muted-foreground" />}
      </div>

      {expanded && (
        <div className="border-t border-border p-4 space-y-3 bg-secondary/10">
          {gate.description && (
            <p className="text-sm text-muted-foreground">{gate.description}</p>
          )}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-secondary rounded-lg p-3">
              <p className="text-muted-foreground mb-1">Status</p>
              <p className={gate.enabled ? "text-emerald-400 font-medium" : "text-muted-foreground"}>
                {gate.enabled ? "Active" : "Disabled"}
              </p>
            </div>
            <div className="bg-secondary rounded-lg p-3">
              <p className="text-muted-foreground mb-1">AI Adaptive</p>
              <p className={gate.adaptive_enabled ? "text-nexus-purple font-medium" : "text-muted-foreground"}>
                {gate.adaptive_enabled ? "Enabled" : "Static threshold only"}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function QualityGatesPage() {
  const [showCreate, setShowCreate] = useState(false);

  const { data: gates = [], isLoading } = useQuery({
    queryKey: ["quality-gates"],
    queryFn: () => api.get("/quality-gates").then(r => r.data),
  });

  const activeCount = gates.filter((g: any) => g.enabled).length;

  return (
    <div className="p-8 space-y-6">
      {showCreate && <CreateGateModal onClose={() => setShowCreate(false)} />}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Quality Gates</h1>
          <p className="text-sm text-muted-foreground">
            AI-adaptive gates that tighten or relax based on deploy context
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 text-sm font-medium transition-all"
        >
          <Plus className="w-4 h-4" />
          New Gate
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Active Gates",   value: activeCount,       icon: Shield,         color: "text-nexus-green" },
          { label: "Total Gates",    value: gates.length,      icon: Shield,         color: "text-muted-foreground" },
          { label: "Blocked Today",  value: 12,                icon: AlertTriangle,  color: "text-nexus-amber" },
          { label: "AI Adaptive",    value: gates.filter((g: any) => g.adaptive_enabled).length, icon: Brain, color: "text-nexus-purple" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="glass rounded-xl p-4 flex items-center gap-3">
            <Icon className={cn("w-5 h-5", color)} />
            <div>
              <p className="text-2xl font-bold">{value}</p>
              <p className="text-xs text-muted-foreground">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* How AI adaptation works */}
      <div className="glass rounded-xl p-5 border border-nexus-purple/20">
        <div className="flex items-center gap-2 mb-3">
          <Brain className="w-4 h-4 text-nexus-purple" />
          <h3 className="text-sm font-medium">How AI Gate Adaptation Works</h3>
        </div>
        <div className="grid grid-cols-3 gap-4 text-xs text-muted-foreground">
          {[
            { ctx: "Friday after 3PM UTC", effect: "Coverage gate tightens +10%, security gate blocks on any HIGH CVE" },
            { ctx: "High-risk diff (score > 70)", effect: "All thresholds tighten proportionally to risk delta" },
            { ctx: "Hotfix branch + #skip-gate tag", effect: "Gates relax to emergency minimums, monitoring agent activates" },
          ].map(({ ctx, effect }) => (
            <div key={ctx} className="bg-secondary rounded-lg p-3 space-y-1">
              <div className="flex items-center gap-1 text-nexus-purple font-medium">
                <Zap className="w-3 h-3" />
                {ctx}
              </div>
              <p>{effect}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Gate list */}
      <div className="space-y-3">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-16 skeleton rounded-xl" />)
          : gates.length > 0
            ? gates.map((g: any) => <GateCard key={g.id} gate={g} />)
            : (
              <div className="text-center py-20 text-muted-foreground">
                <Shield className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p className="font-medium">No gates configured</p>
                <p className="text-sm mt-1">Create your first quality gate to start enforcing standards</p>
                <button
                  onClick={() => setShowCreate(true)}
                  className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:opacity-90"
                >
                  Create Gate
                </button>
              </div>
            )
        }
      </div>
    </div>
  );
}
