"""Capability registry endpoint — serves predefined capability definitions."""

from fastapi import APIRouter

from common.capabilities import CAPABILITY_REGISTRY
from common.schemas.agent import CapabilityResponse

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])


@router.get(
    "",
    response_model=list[CapabilityResponse],
    summary="List predefined capabilities",
    response_description="All available capability definitions with endpoint mappings",
)
def list_capabilities():
    """Return all predefined capabilities that can be assigned to agents.

    Each capability maps to specific API endpoints and HTTP methods.
    Assigning capabilities to an agent auto-generates a gateway policy
    from the union of all selected capabilities' permissions.
    """
    return [
        CapabilityResponse(
            id=cap.id,
            name=cap.name,
            description=cap.description,
            endpoints=list(cap.endpoints),
            methods=list(cap.methods),
        )
        for cap in CAPABILITY_REGISTRY.values()
    ]
