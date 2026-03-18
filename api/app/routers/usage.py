"""Usage & quota endpoints — check limits, view usage, list tiers."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.app.auth import get_current_user
from api.app.quota import get_usage_summary
from common.models import TIER_QUOTAS, User, get_db
from common.schemas.quota import (
    TierInfoResponse,
    TierListResponse,
    UsageSummaryResponse,
)

logger = logging.getLogger("ai_identity.api.usage")

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


# ── GET /api/v1/usage ─────────────────────────────────────────────────


@router.get(
    "",
    response_model=UsageSummaryResponse,
    summary="Get usage summary",
)
def get_usage(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current resource usage against your tier's quota limits.

    Shows agents, keys, credentials, and monthly request counts
    with percentage utilization for each resource.
    """
    summary = get_usage_summary(db, user)
    return UsageSummaryResponse(**summary)


# ── GET /api/v1/usage/tiers ───────────────────────────────────────────


@router.get(
    "/tiers",
    response_model=TierListResponse,
    summary="List available tiers",
)
def list_tiers(
    user: User = Depends(get_current_user),
):
    """List all available subscription tiers with their quota limits."""
    tiers = []
    for name, quotas in TIER_QUOTAS.items():
        tiers.append(
            TierInfoResponse(
                name=name,
                max_agents=quotas["max_agents"],
                max_keys_per_agent=quotas["max_keys_per_agent"],
                max_requests_per_month=quotas["max_requests_per_month"],
                max_credentials=quotas["max_credentials"],
                audit_retention_days=quotas["audit_retention_days"],
            )
        )
    return TierListResponse(tiers=tiers, current_tier=user.tier)
