from fastapi import APIRouter

from app.api.endpoints import heartbeat, code_processing, manual_levers, webui, streaming

api_router = APIRouter()
api_router.include_router(heartbeat.router, prefix='/heartbeat', tags=['heartbeat'])
api_router.include_router(code_processing.router, prefix='/code-processing', tags=['code-processing'])
api_router.include_router(streaming.router, prefix='/streaming', tags=['streaming'])
api_router.include_router(manual_levers.router, prefix='/manual-levers', tags=['manual-levers'])
api_router.include_router(webui.router, prefix='/webui', tags=['webui'])

# api_router.include_router(session_manager.router, prefix='/session', tags=['session'])

# api_router.include_router(s3_test_funcs.router, prefix='/test_s3', tags=['s3'])
