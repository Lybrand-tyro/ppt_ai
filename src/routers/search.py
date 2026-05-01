"""
联网搜索配置路由
"""

from fastapi import APIRouter, Request
from ..search_service import web_search_service
from ..history import JsonHistoryStore
from ..logger import logger
from ..schemas import WebSearchConfigRequest, WebSearchRequest, HistoryApplyRequest
from ..routers.admin import _is_admin_authenticated

router = APIRouter(prefix="/api", tags=["search"])

_web_search_history = JsonHistoryStore("web_search_history.json", max_entries=20)


@router.post("/configure-web-search")
async def configure_web_search(req: WebSearchConfigRequest):
    try:
        kwargs = {"api_key": req.api_key}
        if req.provider == "google" and req.cx:
            kwargs["cx"] = req.cx

        success = web_search_service.configure_provider(req.provider, **kwargs)
        if success:
            masked_key = JsonHistoryStore.mask_api_key(req.api_key)
            entry = {
                "provider": req.provider,
                "api_key_masked": masked_key,
                "api_key": req.api_key,
            }
            if req.cx:
                entry["cx"] = req.cx
            _web_search_history.add(entry, dedup_key="provider")

            logger.info(f"联网搜索配置成功: {req.provider}")
            return {"success": True, "message": f"联网搜索配置成功: {req.provider}"}
        return {"success": False, "message": "配置失败"}
    except Exception as e:
        logger.error(f"联网搜索配置失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/web-search-status")
async def web_search_status():
    return web_search_service.get_provider_status()


@router.post("/web-search")
async def web_search(req: WebSearchRequest):
    if not web_search_service.is_configured():
        return {"success": False, "message": "联网搜索服务未配置"}

    try:
        result = web_search_service.search(req.query, req.max_results)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"联网搜索失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/web-search-history")
async def web_search_history(request: Request):
    if not _is_admin_authenticated(request):
        return {"success": False, "message": "未授权"}
    return {"success": True, "history": _web_search_history.load()}


@router.post("/web-search-history-apply")
async def web_search_history_apply(req: HistoryApplyRequest, request: Request):
    if not _is_admin_authenticated(request):
        return {"success": False, "message": "未授权"}

    history = _web_search_history.load()
    if 0 <= req.index < len(history):
        entry = history[req.index]
        kwargs = {"api_key": entry.get("api_key", "")}
        if entry.get("cx"):
            kwargs["cx"] = entry["cx"]
        web_search_service.configure_provider(entry["provider"], **kwargs)
        logger.info(f"应用搜索历史配置: 索引 {req.index}")
        return {"success": True, "message": "配置已应用"}
    return {"success": False, "message": "无效的索引"}
