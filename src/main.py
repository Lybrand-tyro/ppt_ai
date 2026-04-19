"""
PPT AI - FastAPI主程序
提供PPT生成API，支持LLM生成大纲和内容
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from .llm_service import llm_service
from .ppt_service import ppt_service
from .logger import logger

app = FastAPI(title="PPT AI", description="AI驱动的PPT生成器")

# 静态文件服务
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
    """配置LLM服务

    Args:
        config: LLM配置信息

    Returns:
        配置结果
    """
    logger.info(f"配置LLM: endpoint={config.api_endpoint}, model={config.model_name}, is_local={config.is_local}")
    try:
        llm_service.configure(
            api_endpoint=config.api_endpoint,
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
    """获取LLM配置状态

    Returns:
        LLM状态信息
    """
    return {
        "is_configured": llm_service.is_configured,
        "config": {
            "api_endpoint": llm_service.config.get("api_endpoint", ""),
            "model_name": llm_service.config.get("model_name", ""),
            "is_local": llm_service.config.get("is_local", False)
        } if llm_service.is_configured else None
    }

@app.post("/api/generate-outline")
async def generate_outline(data: dict = Body(...)):
    """生成PPT大纲

    Args:
        data: 包含topic, scenario, language, use_llm的字典

    Returns:
        生成的大纲数据
    """
    topic = data.get("topic")
    scenario = data.get("scenario", "general")
    language = data.get("language", "zh")
    use_llm = data.get("use_llm", False)

    logger.info(f"收到大纲生成请求: topic={topic}, scenario={scenario}, language={language}, use_llm={use_llm}")

    if not topic:
        raise HTTPException(status_code=400, detail="topic不能为空")

    try:
        if use_llm and llm_service.is_configured:
            logger.info("使用LLM生成大纲")
            outline = llm_service.generate_outline(topic, language)
        else:
            logger.info("使用模板生成大纲")
            outline = llm_service._generate_template_outline(topic, language)
        logger.info(f"大纲生成成功: {len(outline.get('slides', []))} 张幻灯片")
        return outline
    except Exception as e:
        logger.error(f"大纲生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成大纲失败: {str(e)}")

@app.post("/api/generate-slides")
async def generate_slides(data: dict = Body(...)):
    """生成PPT幻灯片HTML

    Args:
        data: 包含outline, scenario, use_llm的字典

    Returns:
        生成的HTML内容
    """
    outline = data.get("outline")
    scenario = data.get("scenario", "general")
    use_llm = data.get("use_llm", False)

    logger.info(f"收到幻灯片生成请求: scenario={scenario}, use_llm={use_llm}")

    if not outline:
        raise HTTPException(status_code=400, detail="outline不能为空")

    try:
        slides_html = await ppt_service.generate_html(outline, scenario, use_llm)
        logger.info(f"幻灯片生成成功: {len(slides_html)} 字符")
        return {"slides_html": slides_html}
    except Exception as e:
        logger.error(f"幻灯片生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成幻灯片失败: {str(e)}")

@app.get("/api/logs")
async def get_logs(lines: int = 100):
    """获取日志内容

    Args:
        lines: 返回的日志行数

    Returns:
        日志内容
    """
    try:
        from datetime import datetime
        # 使用绝对路径
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        log_file = os.path.join(log_dir, f"ppt_ai_{datetime.now().strftime('%Y%m%d')}.log")
        logger.info(f"尝试读取日志文件: {log_file}")
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
    """首页"""
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
                "generate_outline": "/api/generate-outline",
                "generate_slides": "/api/generate-slides",
                "logs": "/api/logs"
            }
        }
