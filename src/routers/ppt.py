"""
PPT 生成路由
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..ppt_service import ppt_service
from ..progress import progress_tracker
from ..logger import logger
from ..schemas import GenerateOutlineRequest, GenerateSlidesRequest, DownloadPptxRequest

router = APIRouter(prefix="/api", tags=["ppt"])


@router.post("/generate-outline")
async def generate_outline(req: GenerateOutlineRequest):
    from ..llm_service import llm_service

    try:
        outline = llm_service.generate_outline(
            topic=req.topic,
            language=req.language,
            use_web_search=req.use_web_search,
            task_id=req.task_id
        )
        progress_tracker.complete(req.task_id, "✅ 大纲生成完成")
        return {"success": True, "outline": outline}
    except InterruptedError:
        progress_tracker.cancel(req.task_id)
        return {"success": False, "message": "任务已取消"}
    except Exception as e:
        logger.error(f"大纲生成失败: {e}")
        progress_tracker.fail(req.task_id, f"大纲生成失败: {str(e)}")
        return {"success": False, "message": str(e)}


@router.post("/generate-slides")
async def generate_slides(req: GenerateSlidesRequest):
    try:
        html_content = await ppt_service.generate_html(
            outline=req.outline,
            scenario=req.scenario,
            use_llm=req.use_llm,
            use_web_search=req.use_web_search,
            task_id=req.task_id
        )
        progress_tracker.complete(req.task_id, "✅ PPT生成完成")
        return {"success": True, "html": html_content}
    except InterruptedError:
        progress_tracker.cancel(req.task_id)
        return {"success": False, "message": "任务已取消"}
    except Exception as e:
        logger.error(f"PPT生成失败: {e}")
        progress_tracker.fail(req.task_id, f"PPT生成失败: {str(e)}")
        return {"success": False, "message": str(e)}


@router.post("/download-pptx")
async def download_pptx(req: DownloadPptxRequest):
    try:
        progress_tracker.update(req.task_id, 5, "📊 开始生成PPTX文件...", "pptx_start")
        pptx_bytes = await ppt_service.generate_pptx(
            outline=req.outline,
            scenario=req.scenario,
            use_llm=req.use_llm,
            use_web_search=req.use_web_search
        )
        progress_tracker.complete(req.task_id, "✅ PPTX文件生成完成")

        from urllib.parse import quote
        filename = quote(req.outline.get("title", "presentation"))

        return StreamingResponse(
            iter([pptx_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}.pptx"}
        )
    except Exception as e:
        logger.error(f"PPTX下载失败: {e}")
        progress_tracker.fail(req.task_id, f"PPTX生成失败: {str(e)}")
        return {"success": False, "message": str(e)}
