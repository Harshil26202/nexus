"use client";

import { useState, useCallback } from "react";
import { useWebSocket } from "@/lib/socket";
import { Bot, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";

const AGENTS = [
  "orchestrator", "semantic_analyzer", "test_intelligence",
  "quality_gate", "incident_response", "monitoring", "nl_devops",
];

export function AgentStatusGrid() {
  const [activity, setActivity] = useState<Record<string, { active: boolean; last: string }>>({});

  const onMessage = useCallback((data: unknown) => {
    const evt = data as { event: string; data: { agent?: string; stage?: string } };
    const agentName = evt.data?.agent ?? evt.data?.stage?.replace("_", " ");
    if (agentName) {
      setActivity(prev => ({
        ...prev,
        [agentName]: { active: !evt.event.includes("complete"), last: evt.event },
      }));
    }
  }, []);

  useWebSocket("/agents", onMessage);

  return (
    <div className="grid grid-cols-2 gap-2">
      {AGENTS.map(name => {
        const state = activity[name];
        const isActive = state?.active;
        return (
          <div
            key={name}
            className={cn(
              "flex items-center gap-2 p-2.5 rounded-lg transition-all text-xs",
              isActive ? "bg-nexus-blue/10 border border-nexus-blue/20" : "bg-secondary"
            )}
          >
            <div className={cn(
              "w-6 h-6 rounded-md flex items-center justify-center",
              isActive ? "bg-nexus-blue/20" : "bg-background"
            )}>
              {isActive
                ? <Cpu className="w-3 h-3 text-nexus-blue animate-pulse" />
                : <Bot className="w-3 h-3 text-muted-foreground" />}
            </div>
            <div className="min-w-0">
              <p className={cn("font-medium truncate", isActive ? "text-nexus-blue" : "text-muted-foreground")}>
                {name.replace(/_/g, " ")}
              </p>
              <p className="text-[10px] text-muted-foreground truncate">
                {isActive ? "processing..." : "idle"}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
