# Contributing to NEXUS

## Development Setup

```bash
# Clone and configure
git clone https://github.com/your-org/nexus.git
cd nexus
cp .env.example .env   # fill in Azure credentials

# Start full stack
make dev

# Run tests
make test

# Seed demo data
make seed
```

## Architecture Decisions

- **Agent isolation**: each agent has a single responsibility and communicates only through the orchestrator
- **Async throughout**: FastAPI + asyncpg + async Azure SDKs — no blocking I/O anywhere on the hot path
- **Heuristic fallback**: ML models always have a rule-based fallback so the system degrades gracefully when model artifacts aren't available

## Adding a New Agent

1. Create `backend/app/agents/my_agent.py` subclassing `BaseAgent`
2. Implement `async def run(self, payload: dict) -> AgentResult`
3. Register it in `OrchestratorAgent.__init__()` in `orchestrator.py`
4. Add the corresponding `AgentTask.agent_type` enum value to `models/agent_task.py`
5. Write tests in `backend/tests/test_agents.py`

## Code Style

- Backend: `ruff` (lint) + `mypy --strict` (types) — enforced by CI
- Frontend: `eslint` + `tsc --noEmit` — enforced by CI
- No comments unless the *why* is non-obvious

## PR Checklist

- [ ] `make test` passes locally
- [ ] New agent has a corresponding test in `test_agents.py`
- [ ] Environment variables added to `.env.example`
- [ ] Terraform updated if new Azure resource is used
