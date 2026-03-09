from fastapi import APIRouter
from service import ConfigService

router = APIRouter()
service = ConfigService()


@router.get("/config/{service_name}")
async def get_service_config(service_name: str):
    return service.get_config(service_name)


@router.get("/config")
async def get_all_configs():
    return service.get_all_configs()
