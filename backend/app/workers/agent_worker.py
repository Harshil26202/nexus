"""Service Bus consumer — picks up agent tasks and drives the orchestrator.

Each worker instance processes tasks from 3 queues:
  - nexus-pipeline-events  → run_pipeline
  - nexus-incident-events  → run_incident
  - nexus-agent-tasks      → generic agent dispatch

Runs as a separate process (separate Docker container in prod).
"""
import asyncio
import json
import signal
import sys

import structlog
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage

from app.agents.orchestrator import orchestrator
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.telemetry import setup_telemetry
from app.models.pipeline import Pipeline, PipelineStatus
from app.models.incident import Incident, IncidentStatus

log = structlog.get_logger()
_shutdown = asyncio.Event()


def _handle_signal(sig: int, frame: object) -> None:
    log.info("worker.shutdown_signal", sig=sig)
    _shutdown.set()


async def _update_pipeline_from_result(pipeline_id: str, result: dict) -> None:
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        res = await session.execute(select(Pipeline).where(
            Pipeline.id == __import__("uuid").UUID(pipeline_id)
        ))
        pipeline = res.scalar_one_or_none()
        if not pipeline:
            return
        stages = result.get("stages", {})
        semantic = stages.get("semantic_analysis", {}).get("output", {})
        test_intel = stages.get("test_intelligence", {}).get("output", {})
        gate = stages.get("quality_gate", {}).get("output", {})

        pipeline.status = PipelineStatus.SUCCESS if result.get("can_deploy") else PipelineStatus.FAILED
        pipeline.risk_level = semantic.get("risk_level")
        pipeline.risk_score = semantic.get("risk_score")
        pipeline.semantic_summary = semantic.get("summary")
        pipeline.blast_radius = semantic.get("blast_radius")
        pipeline.selected_tests = test_intel.get("must_run", []) + test_intel.get("should_run", [])
        pipeline.skipped_tests = test_intel.get("skip", [])
        pipeline.gate_results = gate
        pipeline.ai_recommendation = gate.get("risk_summary")
        pipeline.duration_seconds = result.get("total_duration_ms", 0) // 1000
        await session.commit()
        log.info("worker.pipeline_updated", pipeline_id=pipeline_id, status=pipeline.status)


async def _process_pipeline_message(body: dict) -> None:
    pipeline_id = body.get("pipeline_id", "")
    log.info("worker.pipeline_task", pipeline_id=pipeline_id[:8])
    try:
        result = await orchestrator.run_pipeline(body)
        if pipeline_id:
            await _update_pipeline_from_result(pipeline_id, result)
    except Exception as exc:
        log.error("worker.pipeline_task_failed", error=str(exc), pipeline_id=pipeline_id)
        if pipeline_id:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                import uuid
                res = await session.execute(select(Pipeline).where(
                    Pipeline.id == uuid.UUID(pipeline_id)
                ))
                p = res.scalar_one_or_none()
                if p:
                    p.status = PipelineStatus.FAILED
                    await session.commit()


async def _process_incident_message(body: dict) -> None:
    log.info("worker.incident_task", service=body.get("service"))
    try:
        await orchestrator.run_incident(body)
    except Exception as exc:
        log.error("worker.incident_task_failed", error=str(exc))


async def _listen_queue(sb_client: ServiceBusClient, queue_name: str, handler) -> None:
    async with sb_client.get_queue_receiver(queue_name, max_wait_time=5) as receiver:
        while not _shutdown.is_set():
            try:
                messages = await receiver.receive_messages(max_message_count=10, max_wait_time=5)
                for msg in messages:
                    try:
                        body = json.loads(str(msg))
                        await handler(body)
                        await receiver.complete_message(msg)
                    except Exception as exc:
                        log.error("worker.message_failed", queue=queue_name, error=str(exc))
                        await receiver.abandon_message(msg)
            except Exception as exc:
                if not _shutdown.is_set():
                    log.warning("worker.receive_error", queue=queue_name, error=str(exc))
                    await asyncio.sleep(5)


async def main() -> None:
    setup_telemetry()
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    log.info("worker.starting")

    if not settings.AZURE_SERVICE_BUS_CONNECTION_STRING:
        log.warning("worker.no_service_bus — polling mode")
        await _shutdown.wait()
        return

    async with ServiceBusClient.from_connection_string(
        settings.AZURE_SERVICE_BUS_CONNECTION_STRING
    ) as sb_client:
        log.info("worker.service_bus_connected")
        await asyncio.gather(
            _listen_queue(sb_client, settings.AZURE_SERVICE_BUS_QUEUE_PIPELINE, _process_pipeline_message),
            _listen_queue(sb_client, settings.AZURE_SERVICE_BUS_QUEUE_INCIDENTS, _process_incident_message),
        )

    log.info("worker.stopped")


if __name__ == "__main__":
    asyncio.run(main())
