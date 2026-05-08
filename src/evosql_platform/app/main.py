from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from evosql_platform.app.service import QueryService
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

app = FastAPI(title="EvoSQL Campus Smart Query Platform", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
service = QueryService()
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class QueryRequest(BaseModel):
    session_id: str
    question: str
    user_id: str = "demo-user"
    role: str = "admin"
    domain: str = "campus"
    llm_mode: str | None = None


class FollowupRequest(BaseModel):
    answer: str


class LLMConfigRequest(BaseModel):
    display_name: str
    provider: str
    model: str
    base_url: str = ""
    api_key: str = ""
    temperature: float = 0.4
    timeout_seconds: int = 45
    max_retries: int = 2
    scope: str = "campus"
    notes: str = ""


class LLMEnabledRequest(BaseModel):
    enabled: bool


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.post("/api/query")
def create_query(payload: QueryRequest) -> dict:
    task = service.create_query(
        session_id=payload.session_id,
        question=payload.question,
        user_id=payload.user_id,
        role=payload.role,
        domain=payload.domain,
        llm_mode=payload.llm_mode,
    )
    result = task.result
    return {
        "task_id": task.task_id,
        "status": task.status,
        "requires_clarification": result.status == "clarification_required",
        "clarification_question": result.clarification_question,
        "clarification_options": task.pending_clarification.get("options", []) if task.pending_clarification else [],
    }


@app.get("/api/query/{task_id}")
def get_query_result(task_id: str) -> dict:
    try:
        task = service.get_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    result = task.result
    return {
        "task_id": task.task_id,
        "status": task.status,
        "final_sql": result.final_sql,
        "result_rows": result.result_rows,
        "summary_text": result.summary_text,
        "chart_spec": result.chart_spec,
        "used_tables": result.used_tables,
        "used_columns": result.used_columns,
        "safety_checks": result.safety_checks,
        "trace_steps": [asdict(step) for step in result.trace_steps],
        "clarification_question": result.clarification_question,
        "error": result.error,
        "execution_mode": result.execution_mode,
        "result_source": result.result_source,
        "fallback_reason": result.fallback_reason,
        "fallback_applied": result.fallback_applied,
        "candidate_records": result.candidate_records,
        "attempted_candidate_records": result.attempted_candidate_records,
    }


@app.post("/api/query/{task_id}/followup")
def followup(task_id: str, payload: FollowupRequest) -> dict:
    try:
        task = service.followup(task_id, payload.answer)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = task.result
    return {
        "task_id": task.task_id,
        "status": task.status,
        "requires_clarification": result.status == "clarification_required",
        "clarification_question": result.clarification_question,
    }


@app.get("/api/audit/logs")
def audit_logs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    domain: str | None = None,
    llm_mode: str | None = None,
    status: str | None = None,
    result_source: str | None = None,
    query: str | None = None,
) -> dict:
    return service.audit_store.list_logs(
        limit=limit,
        offset=offset,
        domain=domain,
        llm_mode=llm_mode,
        status=status,
        result_source=result_source,
        query=query,
    )


@app.post("/api/audit/reload")
def reload_audit_logs() -> dict:
    return service.audit_store.reload()


@app.get("/api/settings/llms")
def list_llm_configs() -> dict:
    return {"items": service.llm_settings_store.list_configs()}


@app.post("/api/settings/llms")
def create_llm_config(payload: LLMConfigRequest) -> dict:
    try:
        item = service.llm_settings_store.create_config(
            {
                "display_name": payload.display_name,
                "provider": payload.provider,
                "model": payload.model,
                "base_url": payload.base_url,
                "api_key": payload.api_key,
                "temperature": payload.temperature,
                "timeout_seconds": payload.timeout_seconds,
                "max_retries": payload.max_retries,
                "scope": payload.scope,
                "notes": payload.notes,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": item}


@app.put("/api/settings/llms/{config_id}")
def update_llm_config(config_id: str, payload: LLMConfigRequest) -> dict:
    try:
        item = service.llm_settings_store.update_config(
            config_id,
            {
                "display_name": payload.display_name,
                "provider": payload.provider,
                "model": payload.model,
                "base_url": payload.base_url,
                "api_key": payload.api_key,
                "temperature": payload.temperature,
                "timeout_seconds": payload.timeout_seconds,
                "max_retries": payload.max_retries,
                "scope": payload.scope,
                "notes": payload.notes,
            },
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="LLM config not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": item}


@app.post("/api/settings/llms/{config_id}/default")
def set_default_llm(config_id: str) -> dict:
    try:
        item = service.llm_settings_store.set_default(config_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="LLM config not found") from exc
    return {"item": item}


@app.patch("/api/settings/llms/{config_id}/enabled")
def set_llm_enabled(config_id: str, payload: LLMEnabledRequest) -> dict:
    try:
        item = service.llm_settings_store.set_enabled(config_id, payload.enabled)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="LLM config not found") from exc
    return {"item": item}


@app.delete("/api/settings/llms/{config_id}")
def delete_llm_config(config_id: str) -> dict:
    try:
        service.llm_settings_store.delete_config(config_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="LLM config not found") from exc
    return {"deleted": True}
