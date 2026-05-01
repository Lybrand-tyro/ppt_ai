"""
PPT AI - FastAPI主程序
提供PPT生成API，支持LLM生成大纲和内容
支持多种联网搜索API
"""

from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, Optional
import sys
import os
import io
import json
import hashlib
import secrets
from datetime import datetime
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(__file__))

from .llm_service import llm_service, web_search_service
from .ppt_service import ppt_service
from .logger import logger
from .progress import progress_tracker

LLM_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "llm_history.json")
WEB_SEARCH_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web_search_history.json")
ADMIN_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin_config.json")

_admin_tokens: Dict[str, float] = {}

def _hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode('utf-8')).hexdigest()

def _load_admin_config() -> dict:
    if os.path.exists(ADMIN_CONFIG_FILE):
        try:
            with open(ADMIN_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_admin_config(config: dict):
    with open(ADMIN_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def _is_admin(request: Request) -> bool:
    token = request.headers.get('X-Admin-Token', '')
    if not token or token not in _admin_tokens:
        return False
    return True

def _load_llm_history() -> list:
    if os.path.exists(LLM_HISTORY_FILE):
        try:
            with open(LLM_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def _save_llm_history(history: list):
    with open(LLM_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def _add_llm_history(api_endpoint: str, api_key: str, model_name: str, is_local: bool):
    history = _load_llm_history()
    masked_key = (api_key[:4] + "***" + api_key[-4:]) if len(api_key) > 8 else ("***" if api_key else "")
    entry = {
        "api_endpoint": api_endpoint,
        "api_key_masked": masked_key,
        "api_key": api_key,
        "model_name": model_name,
        "is_local": is_local,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    for i, item in enumerate(history):
        if item.get("api_endpoint") == api_endpoint and item.get("model_name") == model_name:
            history[i] = entry
            _save_llm_history(history)
            return
    history.insert(0, entry)
    if len(history) > 20:
        history = history[:20]
    _save_llm_history(history)

def _load_web_search_history() -> list:
    if os.path.exists(WEB_SEARCH_HISTORY_FILE):
        try:
            with open(WEB_SEARCH_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def _save_web_search_history(history: list):
    with open(WEB_SEARCH_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def _add_web_search_history(provider: str, api_key: str = "", cx: str = ""):
    history = _load_web_search_history()
    masked_key = (api_key[:4] + "***" + api_key[-4:]) if len(api_key) > 8 else ("***" if api_key else "")
    entry = {
        "provider": provider,
        "api_key_masked": masked_key,
        "api_key": api_key,
        "cx": cx,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    for i, item in enumerate(history):
        if item.get("provider") == provider:
            history[i] = entry
            _save_web_search_history(history)
            return
    history.insert(0, entry)
    if len(history) > 20:
        history = history[:20]
    _save_web_search_history(history)

app = FastAPI(title="PPT AI", description="AI驱动的PPT生成器")

@app.post("/api/admin-login")
async def admin_login(data: dict = Body(...)):
    password = data.get("password", "")
    config = _load_admin_config()
    stored_hash = config.get("password_hash", "")
    if not stored_hash:
        return {"status": "no_password", "message": "管理员密钥尚未设置", "is_admin": False}
    if _hash_password(password) != stored_hash:
        return {"status": "wrong", "message": "密钥错误", "is_admin": False}
    token = secrets.token_hex(16)
    _admin_tokens[token] = datetime.now().timestamp()
    return {"status": "ok", "token": token, "message": "验证成功", "is_admin": True}

@app.post("/api/admin-set-password")
async def admin_set_password(data: dict = Body(...)):
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
    if not new_password:
        raise HTTPException(status_code=400, detail="新密钥不能为空")
    config = _load_admin_config()
    stored_hash = config.get("password_hash", "")
    if stored_hash and _hash_password(old_password) != stored_hash:
        raise HTTPException(status_code=403, detail="旧密钥错误")
    config["password_hash"] = _hash_password(new_password)
    _save_admin_config(config)
    token = secrets.token_hex(16)
    _admin_tokens[token] = datetime.now().timestamp()
    return {"status": "ok", "token": token, "message": "管理员密钥设置成功"}

@app.get("/api/admin-status")
async def admin_status(request: Request):
    config = _load_admin_config()
    has_password = bool(config.get("password_hash", ""))
    is_admin = _is_admin(request)
    return {"has_password": has_password, "is_admin": is_admin}

@app.post("/api/admin-logout")
async def admin_logout(request: Request):
    token = request.headers.get('X-Admin-Token', '')
    _admin_tokens.pop(token, None)
    return {"status": "ok"}

web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LLMConfig(BaseModel):
    api_endpoint: str
    api_key: str
    model_name: str
    is_local: bool = False

@app.post("/api/configure-llm")
async def configure_llm(config: LLMConfig):
    logger.info(f"配置LLM: endpoint={config.api_endpoint}, model={config.model_name}, is_local={config.is_local}")
    try:
        llm_service.configure(
            api_endpoint=config.api_endpoint,
            api_key=config.api_key,
            model_name=config.model_name,
            is_local=config.is_local
        )
        _add_llm_history(
            api_endpoint=llm_service.config["api_endpoint"],
            api_key=config.api_key,
            model_name=config.model_name,
            is_local=config.is_local
        )
        return {"status": "success", "message": "LLM配置成功"}
    except Exception as e:
        logger.error(f"LLM配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)}")

@app.get("/api/llm-status")
async def get_llm_status():
    return {
        "is_configured": llm_service.is_configured,
        "config": {
            "api_endpoint": llm_service.config.get("api_endpoint", ""),
            "model_name": llm_service.config.get("model_name", ""),
            "is_local": llm_service.config.get("is_local", False)
        } if llm_service.is_configured else None
    }

@app.get("/api/llm-history")
async def get_llm_history(request: Request):
    if not _is_admin(request):
        return {"history": [], "need_admin": True}
    history = _load_llm_history()
    safe_history = []
    for item in history:
        safe_history.append({
            "api_endpoint": item.get("api_endpoint", ""),
            "api_key": item.get("api_key", ""),
            "api_key_masked": item.get("api_key_masked", ""),
            "model_name": item.get("model_name", ""),
            "is_local": item.get("is_local", False),
            "saved_at": item.get("saved_at", "")
        })
    return {"history": safe_history}

@app.post("/api/llm-history-apply")
async def apply_llm_history(request: Request, data: dict = Body(...)):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    index = data.get("index", -1)
    history = _load_llm_history()
    if index < 0 or index >= len(history):
        raise HTTPException(status_code=400, detail="无效的历史配置索引")
    entry = history[index]
    try:
        llm_service.configure(
            api_endpoint=entry["api_endpoint"],
            api_key=entry.get("api_key", ""),
            model_name=entry["model_name"],
            is_local=entry.get("is_local", False)
        )
        return {
            "status": "success",
            "message": "历史配置已应用",
            "config": {
                "api_endpoint": entry["api_endpoint"],
                "api_key": entry.get("api_key", ""),
                "api_key_masked": entry.get("api_key_masked", ""),
                "model_name": entry["model_name"],
                "is_local": entry.get("is_local", False)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"应用配置失败: {str(e)}")

@app.post("/api/configure-web-search")
async def configure_web_search(data: dict = Body(...)):
    provider = data.get("provider")
    if not provider:
        raise HTTPException(status_code=400, detail="provider不能为空")

    try:
        if provider in ("tavily", "serpapi", "bing", "brave"):
            api_key = data.get("api_key", "")
            if not api_key:
                raise HTTPException(status_code=400, detail=f"{provider}需要api_key")
            web_search_service.configure_provider(provider, api_key=api_key)
        elif provider == "google":
            api_key = data.get("api_key", "")
            cx = data.get("cx", "")
            if not api_key or not cx:
                raise HTTPException(status_code=400, detail="Google搜索需要api_key和cx")
            web_search_service.configure_provider(provider, api_key=api_key, cx=cx)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的搜索引擎: {provider}")

        _add_web_search_history(provider, api_key=api_key, cx=cx if provider == "google" else "")

        return {
            "status": "success",
            "message": f"{web_search_service.get_active_provider_name()}联网搜索配置成功",
            "active_provider": web_search_service.active_provider
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"联网搜索配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)}")

@app.get("/api/web-search-status")
async def get_web_search_status():
    return {
        "is_configured": web_search_service.is_configured(),
        "active_provider": web_search_service.active_provider,
        "active_provider_name": web_search_service.get_active_provider_name(),
        "providers": web_search_service.get_provider_status()
    }

@app.get("/api/web-search-history")
async def get_web_search_history(request: Request):
    if not _is_admin(request):
        return {"history": [], "need_admin": True}
    history = _load_web_search_history()
    safe_history = []
    for item in history:
        safe_history.append({
            "provider": item.get("provider", ""),
            "api_key": item.get("api_key", ""),
            "api_key_masked": item.get("api_key_masked", ""),
            "cx": item.get("cx", ""),
            "saved_at": item.get("saved_at", "")
        })
    return {"history": safe_history}

@app.post("/api/web-search-history-apply")
async def apply_web_search_history(request: Request, data: dict = Body(...)):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    index = data.get("index", -1)
    history = _load_web_search_history()
    if index < 0 or index >= len(history):
        raise HTTPException(status_code=400, detail="无效的历史配置索引")
    entry = history[index]
    provider = entry.get("provider", "")
    api_key = entry.get("api_key", "")
    cx = entry.get("cx", "")
    try:
        if provider == "google":
            web_search_service.configure_provider(provider, api_key=api_key, cx=cx)
        else:
            web_search_service.configure_provider(provider, api_key=api_key)
        return {
            "status": "success",
            "message": f"{web_search_service.get_active_provider_name()}历史配置已应用",
            "config": {
                "provider": provider,
                "api_key": api_key,
                "api_key_masked": entry.get("api_key_masked", ""),
                "cx": cx
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"应用配置失败: {str(e)}")

@app.post("/api/web-search")
async def web_search(data: dict = Body(...)):
    query = data.get("query")
    max_results = data.get("max_results", 5)

    if not query:
        raise HTTPException(status_code=400, detail="query不能为空")

    if not web_search_service.is_configured():
        raise HTTPException(status_code=400, detail="联网搜索未配置")

    try:
        result = web_search_service.search(query, max_results=max_results)
        return result
    except Exception as e:
        logger.error(f"联网搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    """SSE端点：实时推送任务进度"""
    import asyncio

    async def event_generator():
        last_progress = -1
        while True:
            status = progress_tracker.get_status(task_id)
            if status["progress"] != last_progress or status["status"] in ("completed", "failed", "cancelled"):
                last_progress = status["progress"]
                yield f"data: {json.dumps(status, ensure_ascii=False)}\n\n"
            if status["status"] in ("completed", "failed", "cancelled", "not_found"):
                progress_tracker.cleanup(task_id)
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/cancel/{task_id}")
async def cancel_task(task_id: str):
    progress_tracker.cancel(task_id)
    return {"status": "cancelled", "task_id": task_id}

@app.post("/api/create-task")
async def create_task():
    task_id = progress_tracker.create_task()
    return {"task_id": task_id}

@app.post("/api/generate-outline")
async def generate_outline(data: dict = Body(...)):
    topic = data.get("topic")
    scenario = data.get("scenario", "general")
    language = data.get("language", "zh")
    use_llm = data.get("use_llm", False)
    use_web_search = data.get("use_web_search", False)
    task_id = data.get("task_id", "")

    logger.info(f"收到大纲生成请求: topic={topic}, use_llm={use_llm}, use_web_search={use_web_search}, task_id={task_id}")

    if not topic:
        raise HTTPException(status_code=400, detail="topic不能为空")

    try:
        if use_llm and llm_service.is_configured:
            logger.info("使用LLM生成大纲")
            import asyncio
            outline = await asyncio.to_thread(llm_service.generate_outline, topic, language, use_web_search, task_id)
        else:
            progress_tracker.update(task_id, 5, "📋 使用模板生成大纲...", "template_outline")
            logger.info("使用模板生成大纲")
            outline = llm_service._generate_template_outline(topic, language)
        progress_tracker.complete(task_id, "✅ 大纲生成完成")
        logger.info(f"大纲生成成功: {len(outline.get('slides', []))} 张幻灯片")
        return outline
    except InterruptedError:
        progress_tracker.cancel(task_id)
        raise HTTPException(status_code=499, detail="任务已取消")
    except Exception as e:
        progress_tracker.fail(task_id, f"❌ 大纲生成失败: {e}")
        logger.error(f"大纲生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成大纲失败: {str(e)}")

@app.post("/api/generate-slides")
async def generate_slides(data: dict = Body(...)):
    outline = data.get("outline")
    scenario = data.get("scenario", "general")
    use_llm = data.get("use_llm", False)
    use_web_search = data.get("use_web_search", False)
    task_id = data.get("task_id", "")

    logger.info(f"收到幻灯片生成请求: scenario={scenario}, use_llm={use_llm}, use_web_search={use_web_search}, task_id={task_id}")

    if not outline:
        raise HTTPException(status_code=400, detail="outline不能为空")

    try:
        progress_tracker.update(task_id, 5, "🚀 开始生成PPT...", "start_slides")
        import asyncio
        slides_html = await ppt_service.generate_html(outline, scenario, use_llm, use_web_search, task_id)
        progress_tracker.complete(task_id, "✅ PPT生成完成")
        logger.info(f"幻灯片生成成功: {len(slides_html)} 字符")
        return {"slides_html": slides_html}
    except InterruptedError:
        progress_tracker.cancel(task_id)
        raise HTTPException(status_code=499, detail="任务已取消")
    except Exception as e:
        progress_tracker.fail(task_id, f"❌ PPT生成失败: {e}")
        logger.error(f"幻灯片生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成幻灯片失败: {str(e)}")

@app.post("/api/download-pptx")
async def download_pptx(data: dict = Body(...)):
    outline = data.get("outline")
    scenario = data.get("scenario", "general")
    use_llm = data.get("use_llm", False)
    use_web_search = data.get("use_web_search", False)

    logger.info(f"收到PPTX下载请求: scenario={scenario}, use_llm={use_llm}, use_web_search={use_web_search}")

    if not outline:
        raise HTTPException(status_code=400, detail="outline不能为空")

    try:
        pptx_bytes = ppt_service.generate_pptx(outline, scenario, use_llm, use_web_search)
        filename = (outline.get("title", "PPT") + ".pptx").replace(" ", "_")
        encoded_filename = quote(filename)
        logger.info(f"PPTX下载成功: {filename}")
        return StreamingResponse(
            io.BytesIO(pptx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except Exception as e:
        logger.error(f"PPTX生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成PPTX失败: {str(e)}")

@app.get("/api/logs")
async def get_logs(request: Request, lines: int = 100):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    try:
        from datetime import datetime
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        log_file = os.path.join(log_dir, f"ppt_ai_{datetime.now().strftime('%Y%m%d')}.log")
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return {"logs": ''.join(all_lines[-lines:])}
        else:
            logger.warning(f"日志文件不存在: {log_file}")
            return {"logs": f"日志文件不存在: {log_file}"}
    except Exception as e:
        logger.error(f"读取日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"读取日志失败: {str(e)}")

@app.get("/")
async def root():
    index_path = os.path.join(web_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {
            "message": "PPT AI API",
            "version": "1.0.0",
            "endpoints": {
                "configure_llm": "/api/configure-llm",
                "llm_status": "/api/llm-status",
                "configure_web_search": "/api/configure-web-search",
                "web_search_status": "/api/web-search-status",
                "web_search": "/api/web-search",
                "generate_outline": "/api/generate-outline",
                "generate_slides": "/api/generate-slides",
                "logs": "/api/logs"
            }
        }
