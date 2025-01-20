from fastapi import APIRouter

from app.api.endpoints import heartbeat

api_router = APIRouter()
api_router.include_router(heartbeat.router, prefix='/heartbeat', tags=['heartbeat'])
# api_router.include_router(session_manager.router, prefix='/session', tags=['session'])

# api_router.include_router(s3_test_funcs.router, prefix='/test_s3', tags=['s3'])
