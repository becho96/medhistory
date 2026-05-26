from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, documents, timeline, reports, interpretations,
    metrics, family, health_events, internal, assistant,
    oauth_consent, mcp_connections, subscription, admin, bot,
    feedback,
)

api_router = APIRouter()

api_router.include_router(internal.router,        prefix="/internal",        tags=["Internal"])
api_router.include_router(auth.router,            prefix="/auth",            tags=["Authentication"])
api_router.include_router(family.router,          prefix="/family",          tags=["Family"])
api_router.include_router(documents.router,       prefix="/documents",       tags=["Documents"])
api_router.include_router(timeline.router,        prefix="/timeline",        tags=["Timeline"])
api_router.include_router(reports.router,         prefix="/reports",         tags=["Reports"])
api_router.include_router(interpretations.router, prefix="/interpretations", tags=["Interpretations"])
api_router.include_router(metrics.router,         prefix="/metrics",         tags=["Metrics"])
api_router.include_router(health_events.router,   prefix="/health-events",   tags=["Health Events"])
api_router.include_router(assistant.router,       prefix="/assistant",       tags=["AI Assistant"])
api_router.include_router(oauth_consent.router,   prefix="/oauth",           tags=["MCP OAuth"])
api_router.include_router(mcp_connections.router, prefix="/mcp",             tags=["MCP Connections"])
api_router.include_router(subscription.router,    prefix="/subscription",    tags=["Subscription"])
api_router.include_router(admin.router,           prefix="/admin",           tags=["Admin"])
api_router.include_router(bot.router,             prefix="/bot",             tags=["Telegram Bot"])
api_router.include_router(feedback.router,        prefix="/feedback",        tags=["Feedback"])

