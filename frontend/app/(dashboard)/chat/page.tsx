"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Zap, RotateCcw, Copy } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import toast from "react-hot-toast";

interface Message {
  role: "user" | "assistant";
  content: string;
  tools?: Array<{ tool: string; params: Record<string, unknown> }>;
  suggestions?: string[];
  loading?: boolean;
}

const SUGGESTED = [
  "What's the risk level of the last 5 deployments?",
  "Show me open incidents and their severity",
  "Which agents are currently active?",
  "What pipelines failed in the last hour?",
  "Create an incident for payment service latency spike",
];

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";

  const copyContent = () => {
    navigator.clipboard.writeText(msg.content);
    toast.success("Copied");
  };

  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      {/* Avatar */}
      <div
        className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
          isUser ? "bg-nexus-blue/20" : "bg-nexus-purple/20"
        )}
      >
        {isUser ? <User className="w-4 h-4 text-nexus-blue" /> : <Bot className="w-4 h-4 text-nexus-purple" />}
      </div>

      {/* Bubble */}
      <div className={cn("max-w-2xl space-y-2", isUser ? "items-end" : "items-start")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm",
            isUser
              ? "bg-nexus-blue/15 border border-nexus-blue/20 rounded-tr-sm"
              : "glass border border-border rounded-tl-sm"
          )}
        >
          {msg.loading ? (
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-nexus-purple rounded-full animate-bounce [animation-delay:-0.3s]" />
              <span className="w-1.5 h-1.5 bg-nexus-purple rounded-full animate-bounce [animation-delay:-0.15s]" />
              <span className="w-1.5 h-1.5 bg-nexus-purple rounded-full animate-bounce" />
            </div>
          ) : (
            <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
          )}
        </div>

        {/* Tool calls */}
        {msg.tools && msg.tools.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {msg.tools.map((t, i) => (
              <div key={i} className="text-xs bg-nexus-purple/10 border border-nexus-purple/20 text-nexus-purple px-2 py-1 rounded-full flex items-center gap-1">
                <Zap className="w-3 h-3" />
                {t.tool}
              </div>
            ))}
          </div>
        )}

        {/* Follow-up suggestions */}
        {msg.suggestions && msg.suggestions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {msg.suggestions.map((s, i) => (
              <button
                key={i}
                className="text-xs text-muted-foreground border border-border rounded-full px-3 py-1 hover:text-foreground hover:border-muted-foreground transition-all"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Copy */}
        {!isUser && !msg.loading && (
          <button
            onClick={copyContent}
            className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
          >
            <Copy className="w-3 h-3" /> Copy
          </button>
        )}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hey! I'm NEXUS NL DevOps — your natural language interface to the delivery platform. Ask me to check pipeline status, create incidents, assess deployment risk, or trigger rollbacks. What do you need?",
      suggestions: SUGGESTED.slice(0, 3),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: Message = { role: "user", content: text };
    const placeholder: Message = { role: "assistant", content: "", loading: true };

    setMessages(prev => [...prev, userMsg, placeholder]);
    setInput("");
    setLoading(true);

    try {
      const history = messages
        .filter(m => !m.loading)
        .map(m => ({ role: m.role, content: m.content }));

      const resp = await api.post("/chat/public", {
        message: text,
        history,
      });

      const d = resp.data;
      setMessages(prev => [
        ...prev.slice(0, -1),
        {
          role: "assistant",
          content: d.response || "Done.",
          tools: d.tools_called || [],
          suggestions: d.follow_up_suggestions || [],
        },
      ]);
    } catch {
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: "assistant", content: "Something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-border glass">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-nexus-purple/20 flex items-center justify-center">
            <Bot className="w-5 h-5 text-nexus-purple" />
          </div>
          <div>
            <h1 className="font-bold">NL DevOps</h1>
            <p className="text-xs text-muted-foreground">Natural language interface to your delivery platform</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Suggested commands */}
      {messages.length === 1 && (
        <div className="px-6 pb-4 flex flex-wrap gap-2">
          {SUGGESTED.map((s, i) => (
            <button
              key={i}
              onClick={() => send(s)}
              className="text-xs border border-border rounded-full px-3 py-1.5 text-muted-foreground hover:text-foreground hover:border-muted-foreground transition-all"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-border glass">
        <form
          onSubmit={e => { e.preventDefault(); send(input); }}
          className="flex items-center gap-3"
        >
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask anything about your pipelines, deployments, incidents..."
            disabled={loading}
            className="flex-1 bg-secondary border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="p-3 bg-primary text-primary-foreground rounded-xl hover:opacity-90 disabled:opacity-40 transition-all"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
