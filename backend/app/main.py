import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.api.v1 import (
    assistant, auth, automations, calendar, commitments, context, dashboard,drive,
    deadlines, inbox, integrations, knowledge, meetings, memory, notifications,
    opportunities, priorities, projects, risks, tasks, users, waiting_for,
    weekly_review, workspaces,
)
from app.core.config import settings
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models.workspace import Workspace  # noqa: F401 - ensures all models are imported for metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("operator-ai")

app = FastAPI(title="Operator AI", version="1.0.0", description="AI Chief of Staff API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = settings.API_PREFIX

_ROUTERS = (
    auth.router, users.router, workspaces.router, tasks.router, projects.router,
    calendar.router,drive.router, meetings.router, commitments.router, waiting_for.router,
    deadlines.router, knowledge.router, memory.router, context.router, risks.router,
    opportunities.router, weekly_review.router, automations.router, notifications.router,
    inbox.router, priorities.router, assistant.router, dashboard.router, integrations.router,
)
for router in _ROUTERS:
    app.include_router(router, prefix=API_PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok"}


async def _run_due_automations_for_all_workspaces():

    from app.workers.automation_runner import run_workspace_automations

    async with AsyncSessionLocal() as db:
        workspace_ids = (await db.execute(select(Workspace.id))).scalars().all()
        for ws_id in workspace_ids:
            try:
                await run_workspace_automations(db, ws_id)
            except Exception:
                logger.exception("automation run failed for workspace %s", ws_id)


_scheduler = AsyncIOScheduler()


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:

        if settings.ENV == "development":
            await conn.run_sync(Base.metadata.create_all)

    _scheduler.add_job(_run_due_automations_for_all_workspaces, "interval", minutes=15, id="automations")
    _scheduler.start()


@app.on_event("shutdown")
async def on_shutdown():
    _scheduler.shutdown(wait=False)
