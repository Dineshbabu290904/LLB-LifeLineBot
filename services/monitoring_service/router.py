from fastapi import APIRouter, HTTPException
from service import check_all_services, check_single_service, SERVICE_REGISTRY

router = APIRouter()


@router.get("/health/all")
async def health_all():
    """Poll every registered MEDBOT service /health endpoint concurrently."""
    report = await check_all_services()
    return report


@router.get("/health/{service_name}")
async def health_single(service_name: str):
    """Poll the /health endpoint of a specific service by name."""
    result = await check_single_service(service_name)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found in registry. "
                   f"Known services: {sorted(SERVICE_REGISTRY.keys())}",
        )
    return result


@router.get("/services")
async def list_services():
    """Return the list of all registered services and their base URLs."""
    return {
        "total": len(SERVICE_REGISTRY),
        "services": [
            {"name": name, "base_url": url}
            for name, url in sorted(SERVICE_REGISTRY.items())
        ],
    }
