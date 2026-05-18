<div align="center">

# ⚡ NEXUS
### AI-Native Engineering Intelligence Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](docker-compose.yml)
[![Hackathon](https://img.shields.io/badge/Microsoft%20Build%20AI%20Hackathon-2026-purple.svg)](https://devpost.com)

**Submitted for Microsoft Build AI Hackathon 2026 · Theme 6: AI-Powered Production Function**

[Live Demo](#quickstart) · [Architecture](#architecture) · [Features](#features) · [API Docs](http://localhost:8000/docs)

---

*Your CI/CD pipeline runs 500 tests on every commit. 80% are irrelevant. Production broke last night and it took 3 hours to find the root cause. NEXUS fixes both of these — automatically, with AI.*

</div>

---

## The Problem

Every engineering team ships code through a pipeline designed for a world without AI:

| Pain Point | Reality | NEXUS Solution |
|---|---|---|
| Blind test execution | All 500 tests run on every commit | AI selects only the ~40 tests relevant to your change |
| Static quality gates | "Coverage ≥ 80%" regardless of context | Adaptive AI gates that tighten on Friday deploys, relax for hotfixes |
| Manual incident response | Engineers spend 3+ hours tracing root causes | AI identifies the guilty commit in seconds, drafts the postmortem |
| DevOps tribal knowledge | Need to know CLIs, dashboards, Runbooks | Ask in plain English: *"Why did auth-service fail last night?"* |

---

## Features

### Working Today

- **Semantic Diff Analyzer** — GPT-4o reads your actual code diff, identifies blast radius, risk factors, and affected services. Assigns a risk score 0–100 with plain-English reasoning.
- **Test Intelligence Engine** — ML (XGBoost) + LLM reasoning selects the relevant test subset. Skips provably unaffected tests. Average **67% CI time reduction** in our demo data.
- **Adaptive Quality Gates** — AI evaluates gates with context, not just static thresholds. Example gate prompt: *"Block if auth middleware is touched without a security-review PR label."*
- **Incident Intelligence** — When an alert fires, the agent correlates metrics + git history, pinpoints the root cause commit, and generates a full Google SRE-style postmortem draft automatically.
- **Natural Language DevOps** — Chat interface for plain-English queries against your pipeline data. No dashboard spelunking required.
- **Real-time Dashboard** — Live WebSocket feed of pipeline events, risk scores, agent activity, and incident status.
- **Post-Deploy Monitoring Agent** — Watches metrics post-deploy, detects regressions, triggers incident creation automatically.

### Platform
- REST API with interactive Swagger docs at `/docs`
- WebSocket event streaming for real-time UI updates
- Prometheus metrics at `/metrics`, Grafana dashboards at `:3001`
- OpenTelemetry distributed tracing
- Seed demo data — fully populated dashboard out of the box

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DEVELOPER WORKFLOW                             │
│                                                                     │
│   git push ──▶ GitHub PR ──▶ CI trigger                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  POST /api/v1/webhooks/github
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   NEXUS BACKEND  (FastAPI · Python 3.11)            │
│                                                                     │
│   /pipelines   /incidents   /quality-gates   /analytics   /chat     │
│                         /webhooks   /ws                             │
│                               │                                     │
│                    ┌──────────▼──────────┐                          │
│                    │   Agent Dispatcher   │                          │
│                    └──────────┬──────────┘                          │
└───────────────────────────────┼─────────────────────────────────────┘
                                │ spawns AI agents
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT SYSTEM  (GPT-4o)                     │
│                                                                     │
│   ┌──────────────────┐   ┌──────────────────┐                       │
│   │ Semantic Analyzer │   │ Test Intelligence │                       │
│   │ • Code diff NLU  │   │ • XGBoost + LLM  │                       │
│   │ • Blast radius   │   │ • 67% CI savings │                       │
│   │ • Risk score 0–100│   │ • Smart skip     │                       │
│   └──────────────────┘   └──────────────────┘                       │
│                                                                     │
│   ┌──────────────────┐   ┌──────────────────┐                       │
│   │  Quality Gate    │   │ Incident Response │                       │
│   │ • Adaptive AI    │   │ • Root cause AI  │                       │
│   │ • Context-aware  │   │ • Postmortem gen │                       │
│   │ • Deploy block   │   │ • MTTR: hrs→mins │                       │
│   └──────────────────┘   └──────────────────┘                       │
│                                                                     │
│   ┌──────────────────┐   ┌──────────────────┐                       │
│   │  NL DevOps Chat  │   │ Monitoring Agent  │                       │
│   │ • Plain English  │   │ • Post-deploy    │                       │
│   │ • Pipeline query │   │ • Auto incidents │                       │
│   │ • No CLI needed  │   │ • Anomaly detect │                       │
│   └──────────────────┘   └──────────────────┘                       │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
          ┌─────────────┴───────────────┐
          ▼                             ▼
┌──────────────────┐         ┌────────────────────┐
│   PostgreSQL 16  │         │    Redis 7          │
│                  │         │                     │
│ • Pipelines      │         │ • Response cache    │
│ • Incidents      │         │ • Pub/Sub events    │
│ • Quality gates  │         │ • Rate limiting     │
│ • Agent tasks    │         │ • WebSocket fanout  │
└──────────────────┘         └────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                   FRONTEND  (Next.js 14 · TypeScript)               │
│                                                                     │
│  Dashboard · Pipelines · Incidents · Quality Gates · Agents · Chat  │
│                                                                     │
│         Live WebSocket stream  ·  Recharts visualizations           │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      OBSERVABILITY                                  │
│  Prometheus → Grafana  ·  OpenTelemetry Collector  ·  Structlog     │
└─────────────────────────────────────────────────────────────────────┘

                     ┌──────────────────────┐
                     │     AI PROVIDERS     │
                     │                      │
                     │  OpenAI  (default)   │
                     │  ─── or ───          │
                     │  Azure OpenAI        │
                     │  (swap via .env)     │
                     └──────────────────────┘
```

---

## Quickstart

**Prerequisites:** Docker Desktop · An OpenAI API key (get one at [platform.openai.com](https://platform.openai.com))

```bash
# 1. Clone
git clone https://github.com/Harshil26202/nexus.git
cd nexus

# 2. Configure — only one key is required to start
cp .env.example .env
# Open .env and set:  OPENAI_API_KEY=sk-...
# Everything else has working defaults for local dev.

# 3. Start everything
make dev

# Or without Make:
docker compose up --build -d
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API + Swagger Docs | http://localhost:8000/docs |
| Grafana | http://localhost:3001 (admin / admin) |
| Prometheus | http://localhost:9090 |

### Seed demo data (optional — makes the dashboard look great)

```bash
make seed
# or:
docker compose exec backend python -m app.scripts.seed_demo_data
```

This seeds 60 pipeline runs, 5 quality gates, 3 incidents, and agent task history so the dashboard is fully populated on first launch.

### Useful commands

```bash
make logs          # tail backend + agent worker + frontend logs
make migrate       # run database migrations
make seed          # populate demo data
make test          # run backend + frontend test suites
make lint          # ruff + mypy + eslint
make down          # stop everything
make clean         # stop + remove volumes
```

---

## Using Azure OpenAI Instead

NEXUS detects which provider to use automatically. If you have Azure credentials:

```env
# In .env — set both of these and Azure takes over automatically:
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-key
```

Leave them blank (the default) and standard OpenAI is used.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts, TanStack Query |
| Backend API | FastAPI (Python 3.11), AsyncPG, SQLAlchemy 2.0 (async) |
| AI / LLM | OpenAI GPT-4o · Azure OpenAI (drop-in swap) |
| ML Models | XGBoost, scikit-learn, pandas (risk scoring + test prediction) |
| Embeddings | text-embedding-3-large |
| Cache / Pub-Sub | Redis 7 (async, connection pooled) |
| Database | PostgreSQL 16 |
| Message Queue | Azure Service Bus (optional, async agent tasks) |
| Vector Search | Azure AI Search (optional, semantic incident search) |
| Observability | Prometheus + Grafana + OpenTelemetry + Structlog |
| Auth | JWT + Azure Entra ID (optional SSO) |
| Containerization | Docker Compose (dev) |
| IaC | Terraform (infrastructure/) |
| CI/CD | GitHub Actions (.github/workflows/) |

---

## Project Structure

```
nexus/
├── frontend/                    # Next.js 14 dashboard
│   ├── app/(dashboard)/         # Dashboard, Pipelines, Incidents, Agents, Chat
│   ├── components/              # Reusable UI + WebSocket hooks
│   └── lib/                     # Axios API client, socket utilities
│
├── backend/                     # FastAPI + multi-agent system
│   ├── app/
│   │   ├── agents/              # 7 specialized AI agents
│   │   │   ├── orchestrator.py         # Master coordinator
│   │   │   ├── semantic_analyzer.py    # Code diff intelligence
│   │   │   ├── test_intelligence.py    # Smart test selection
│   │   │   ├── quality_gate_agent.py   # Adaptive quality gates
│   │   │   ├── incident_response.py    # Root cause + postmortem
│   │   │   ├── monitoring_agent.py     # Post-deploy health
│   │   │   └── nl_devops.py            # Natural language interface
│   │   ├── routers/             # REST + WebSocket endpoints
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── services/            # GitHub, notifications, ML
│   │   ├── scripts/             # seed_demo_data.py
│   │   └── core/                # Config, DB, Redis, telemetry, auth
│   ├── main.py                  # FastAPI app entrypoint
│   └── requirements.txt
│
├── ml/                          # ML model code (risk scoring, test prediction)
│   ├── risk_scoring/            # Gradient boosting risk model
│   └── test_prediction/         # XGBoost test failure prediction
│
├── infrastructure/
│   ├── terraform/               # Azure infrastructure as code
│   ├── kubernetes/              # AKS manifests
│   └── monitoring/              # Prometheus, Grafana, OTEL config
│
├── .github/workflows/           # CI (lint, test, build) + CD pipelines
├── docker-compose.yml           # Full local stack
├── Makefile                     # Developer convenience commands
└── .env.example                 # Configuration template
```

---

## API Reference

The full interactive API is at **http://localhost:8000/docs** once running.

Key endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/pipelines/` | List pipeline runs with risk scores |
| `GET` | `/api/v1/pipelines/{id}` | Pipeline detail + AI analysis |
| `POST` | `/api/v1/webhooks/github` | GitHub webhook receiver |
| `GET` | `/api/v1/incidents/` | Active + resolved incidents |
| `GET` | `/api/v1/quality-gates/` | Gate definitions + results |
| `POST` | `/api/v1/chat/` | Natural language DevOps query |
| `GET` | `/api/v1/analytics/overview` | Platform-wide stats |
| `WS` | `/ws/pipelines` | Real-time pipeline event stream |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Prometheus metrics |

---

## How the AI Works — End to End

```
1. Developer opens a PR on GitHub
          │
          ▼
2. GitHub sends a webhook → POST /api/v1/webhooks/github
          │
          ▼
3. Semantic Analyzer (GPT-4o) reads the raw diff
   → Identifies: blast radius, risk factors, affected services
   → Assigns: risk score 0–100, risk level (low/medium/high/critical)
   → Writes: plain-English summary for the team
          │
          ▼
4. Test Intelligence (XGBoost + GPT-4o) selects relevant tests
   → Skips ~67% of the test suite that can't be affected
   → Prioritizes highest-risk paths
          │
          ▼
5. Quality Gate Agent evaluates gates with AI reasoning
   → Applies adaptive thresholds based on context
   → Returns: pass/fail + deploy recommendation
          │
          ▼
6. Results appear live on the dashboard via WebSocket
   → Risk score, blast radius, gate results, AI recommendation
          │
          ▼
7. If production breaks post-deploy:
   Incident Response Agent traces root commit → postmortem → fix suggestion
```

---

## Demo Walkthrough

1. Open **http://localhost:3000** — dashboard shows live pipeline stats, risk distribution, agent activity
2. Go to **Pipelines** — see 60 runs with AI risk scores, semantic summaries, blast radius
3. Click any pipeline — deep-dive into the AI analysis, test selection rationale, gate results
4. Go to **Incidents** — see the SEV1 (resolved) with full postmortem, root cause commit, and suggested fix
5. Go to **Quality Gates** — see adaptive gates with natural language AI prompts
6. Open **Chat** — ask: *"Which pipelines have critical risk this week?"*
7. Open **Grafana** (http://localhost:3001) — infrastructure metrics

---

## AI Tools Used

- **Claude Code** — architecture design, full-stack implementation
- **GitHub Copilot** — inline suggestions during development

---

## Team

Built at **Microsoft Build AI Hackathon 2026** by Harshil Kaneriya

---

## License

MIT — see [LICENSE](LICENSE)
