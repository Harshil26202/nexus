"use client";

import { useState, useCallback } from "react";
import { useWebSocket } from "@/lib/socket";
import { GitBranch, CheckCircle2, XCircle, Shield, Zap, Eye } from "lucide-react";
import { cn } from "@/lib/utils";

interface PipelineEvent {
  event: string;
  pipeline_id: string;
  data: Record<string, unknown>;
  timestamp: number;
}

const EVENT_CONFIG: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  pipeline_started:   { icon: GitBranch,    color: "text-blue-400",    label: "Pipeline started" },
  stage_started:      { icon: Zap,          color: "text-amber-400",   label: "Stage running" },
  stage_complete:     { icon: CheckCircle2, color: "text-emerald-400", label: "Stage complete" },
  pipeline_complete:  { icon: CheckCircle2, color: "text-emerald-400", label: "Pipeline done" },
  rollback_recommended: { icon: Shield,     color: "text-red-400",     label: "Rollback recommended" },
};

export function LivePipelineStream() {
  const [events, setEvents] = useState<PipelineEvent[]>([]);

  const onMessage = useCallback((data: unknown) => {
    const evt = data as PipelineEvent;
    setEvents(prev => [evt, ...prev].slice(0, 50));
  }, []);

  useWebSocket("/pipelines", onMessage);

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
        <div className="text-center">
          <Eye className="w-8 h-8 mx-auto mb-2 opacity-30" />
          Watching for pipeline events...
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
      {events.map((evt, i) => {
        const cfg = EVENT_CONFIG[evt.event] ?? { icon: Zap, color: "text-muted-foreground", label: evt.event };
        const Icon = cfg.icon;
        return (
          <div key={i} className="flex items-start gap-3 text-xs">
            <Icon className={cn("w-3 h-3 mt-0.5 flex-shrink-0", cfg.color)} />
            <div className="flex-1 min-w-0">
              <span className={cn("font-medium", cfg.color)}>{cfg.label}</span>
              <span className="text-muted-foreground ml-2">
                {evt.pipeline_id?.slice(0, 8)}
              </span>
              {evt.data?.stage && (
                <span className="text-muted-foreground ml-1">· {evt.data.stage as string}</span>
              )}
              {evt.data?.risk_level && (
                <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] bg-secondary">
                  {evt.data.risk_level as string}
                </span>
              )}
            </div>
            <span className="text-muted-foreground flex-shrink-0">
              {new Date(evt.timestamp * 1000).toLocaleTimeString()}
            </span>
          </div>
        );
      })}
    </div>
  );
}
