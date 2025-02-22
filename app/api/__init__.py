from fastapi import APIRouter

from app.api.endpoints import heartbeat, code_import, manual_levers, webui, streaming, code_process, code_export

api_router = APIRouter()
api_router.include_router(heartbeat.router, prefix='/heartbeat', tags=['heartbeat'])
api_router.include_router(code_import.router, prefix='/code-import', tags=['import'])
api_router.include_router(code_process.router, prefix='/code-process', tags=['process'])
api_router.include_router(code_export.router, prefix='/code-export', tags=['export'])
api_router.include_router(streaming.router, prefix='/streaming', tags=['streaming'])

api_router.include_router(manual_levers.router, prefix='/manual-levers', tags=['manual-levers'])
api_router.include_router(webui.router, prefix='/webui', tags=['webui'])

# api_router.include_router(session_manager.router, prefix='/session', tags=['session'])

# api_router.include_router(s3_test_funcs.router, prefix='/test_s3', tags=['s3'])
