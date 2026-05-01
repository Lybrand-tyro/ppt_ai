"""
LLM 配置路由
"""

from fastapi import APIRouter, Request
from ..llm_service import llm_service
from ..history import JsonHistoryStore
from ..logger import logger
from ..schemas import LLMConfigRequest, HistoryApplyRequest
from ..routers.admin import _is_admin_authenticated

router = APIRouter(prefix="/api", tags=["llm"])

_llm_history = JsonHistoryStore("llm_history.json", max_entries=20)


@router.post("/configure-llm")
async def configure_llm(req: LLMConfigRequest):
    try:
        llm_service.configure(req.api_endpoint, req.api_key, req.model_name, req.is_local)

        masked_key = JsonHistoryStore.mask_api_key(req.api_key)
        _llm_history.add({
            "api_endpoint": req.api_endpoint,
            "api_key_masked": masked_key,
            "api_key": req.api_key,
            "model_name": req.model_name,
            "is_local": req.is_local,
        }, dedup_key="api_endpoint")

        logger.info("LLM配置成功")
        return {"success": True, "message": "LLM配置成功"}
    except Exception as e:
        logger.error(f"LLM配置失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/llm-status")
async def llm_status():
    return {
        "is_configured": llm_service.is_configured,
        "api_endpoint": llm_service.config.get("api_endpoint", ""),
        "model_name": llm_service.config.get("model_name", ""),
        "is_local": llm_service.config.get("is_local", False),
        "api_key_masked": JsonHistoryStore.mask_api_key(llm_service.config.get("api_key", ""))
    }


@router.get("/llm-history")
async def llm_history(request: Request):
    if not _is_admin_authenticated(request):
        return {"success": False, "message": "未授权"}
    return {"success": True, "history": _llm_history.load()}


@router.post("/llm-history-apply")
async def llm_history_apply(req: HistoryApplyRequest, request: Request):
    if not _is_admin_authenticated(request):
        return {"success": False, "message": "未授权"}

    history = _llm_history.load()
    if 0 <= req.index < len(history):
        entry = history[req.index]
        llm_service.configure(
            entry["api_endpoint"],
            entry["api_key"],
            entry["model_name"],
            entry.get("is_local", False)
        )
        logger.info(f"应用LLM历史配置: 索引 {req.index}")
        return {"success": True, "message": "配置已应用"}
    return {"success": False, "message": "无效的索引"}
