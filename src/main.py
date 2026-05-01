"""
PPT AI - FastAPI 主程序
"""

import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .logger import logger
from .routers import admin_router, llm_router, search_router, ppt_router, progress_router

app = FastAPI(title="PPT AI", description="智能PPT生成器")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(llm_router)
app.include_router(search_router)
app.include_router(ppt_router)
app.include_router(progress_router)

_web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
_log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


@app.get("/")
async def index():
    index_path = os.path.join(_web_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "PPT AI Service Running"}


@app.get("/api/logs")
async def get_logs(request: Request, lines: int = 100):
    from .routers.admin import _is_admin_authenticated

    if not _is_admin_authenticated(request):
        return {"success": False, "message": "未授权"}

    from datetime import datetime
    log_file = os.path.join(_log_dir, f"ppt_ai_{datetime.now().strftime('%Y%m%d')}.log")
    if not os.path.exists(log_file):
        return {"success": True, "logs": ""}

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        return {"success": True, "logs": "".join(all_lines[-lines:])}
    except Exception as e:
        return {"success": False, "message": str(e)}


logger.info("PPT AI 服务启动")
