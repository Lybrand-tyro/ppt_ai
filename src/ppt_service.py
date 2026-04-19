"""
PPT生成服务模块
负责生成HTML和PPTX格式的PPT
"""

from typing import Dict, Any, List
from .llm_service import llm_service
from .logger import logger

JAVASCRIPT_CODE = """
let slideCurrent = 0;
let slideTotal = 7;

function showSlide(n) {
    const slides = document.querySelectorAll('.slide');
    if (!slides || slides.length === 0) return;
    slideCurrent = n;
    if (slideCurrent >= slideTotal) slideCurrent = 0;
    if (slideCurrent < 0) slideCurrent = slideTotal - 1;
    slides.forEach(function(slide) {
        if (slide) {
            slide.style.display = 'none';
            slide.classList.remove('active');
        }
    });
    if (slides[slideCurrent]) {
        slides[slideCurrent].style.display = 'flex';
        slides[slideCurrent].classList.add('active');
    }
    var counter = document.getElementById('slideCounter');
    if (counter) counter.textContent = (slideCurrent + 1) + ' / ' + slideTotal;
}

function nextSlide() { showSlide(slideCurrent + 1); }
function prevSlide() { showSlide(slideCurrent - 1); }

function initSlides(total) {
    slideTotal = total || 7;
    slideCurrent = 0;
    showSlide(0);
    document.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
        if (e.key === 'ArrowLeft') prevSlide();
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    if (prevBtn) prevBtn.addEventListener('click', prevSlide);
    if (nextBtn) nextBtn.addEventListener('click', nextSlide);
});
"""

class PPTService:
    """PPT生成服务"""

    def __init__(self):
        self.scenario_configs = {
            "general": {
                "color_scheme": "#2E86AB",
                "font_family": "Microsoft YaHei, Arial, sans-serif",
                "style_class": "general-theme"
            },
            "technology": {
                "color_scheme": "#3498DB",
                "font_family": "Consolas, monospace",
                "style_class": "tech-theme"
            },
            "business": {
                "color_scheme": "#27AE60",
                "font_family": "Microsoft YaHei, Arial, sans-serif",
                "style_class": "business-theme"
            },
            "education": {
                "color_scheme": "#9B59B6",
                "font_family": "Microsoft YaHei, Arial, sans-serif",
                "style_class": "education-theme"
            },
            "tourism": {
                "color_scheme": "#E67E22",
                "font_family": "Microsoft YaHei, Arial, sans-serif",
                "style_class": "tourism-theme"
            },
            "science": {
                "color_scheme": "#1ABC9C",
                "font_family": "Microsoft YaHei, Arial, sans-serif",
                "style_class": "science-theme"
            }
        }

    async def generate_html(self, outline: Dict[str, Any], scenario: str = "general", use_llm: bool = False) -> str:
        """生成HTML格式的PPT

        Args:
            outline: 大纲数据
            scenario: 应用场景
            use_llm: 是否使用LLM生成内容

        Returns:
            HTML字符串
        """
        logger.info(f"开始生成HTML PPT: scenario={scenario}, use_llm={use_llm}")

        config = self.scenario_configs.get(scenario, self.scenario_configs["general"])
        topic = outline.get("title", "")
        language = outline.get("metadata", {}).get("language", "zh")

        slides_html = []
        slide_id = 1

        for slide in outline.get("slides", []):
            slide_type = slide.get("type", "content")
            title = slide.get("title", "")
            enriched_slide = slide.copy()

            if slide_type == "content" and use_llm and llm_service.is_configured:
                logger.info(f"使用LLM生成幻灯片内容: {title}")
                try:
                    content = llm_service.generate_content(title, slide_type, topic, language)
                    enriched_slide["content"] = content
                    logger.info(f"LLM内容生成成功: {title}")
                except Exception as e:
                    logger.error(f"LLM内容生成失败: {e}")

            if slide_type == "content":
                expanded_slides = self._expand_slide_with_template(enriched_slide, topic)
                for exp_slide in expanded_slides:
                    exp_slide["id"] = slide_id
                    slides_html.append(self._generate_slide_html(exp_slide, config))
                    slide_id += 1
            else:
                enriched_slide["id"] = slide_id
                slides_html.append(self._generate_slide_html(enriched_slide, config))
                slide_id += 1

        total_slides = len(slides_html)
        css_styles = self._generate_css_styles(config)

        complete_html = f"""<!DOCTYPE html>
<html lang="{language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{outline.get('title', 'PPT')}</title>
    <style>
        {css_styles}
    </style>
</head>
<body>
    <div class="presentation-container">
        <div class="slides-wrapper">
            {''.join(slides_html)}
        </div>
        <div class="navigation">
            <button id="prevBtn">‹ 上一页</button>
            <span id="slideCounter">1 / {total_slides}</span>
            <button id="nextBtn">下一页 ›</button>
        </div>
    </div>

    <script>
        {JAVASCRIPT_CODE}
        initSlides({total_slides});
    </script>
</body>
</html>
        """
        logger.info(f"HTML PPT生成完成: {total_slides} 张幻灯片, {len(complete_html)} 字符")
        return complete_html

    def _expand_slide_with_template(self, slide: Dict[str, Any], topic: str) -> List[Dict[str, Any]]:
        """使用模板扩展内容幻灯片"""
        title = slide.get("title", "")
        content = slide.get("content", "")

        points = self._parse_bullet_points(content)
        slides = []
        points_per_slide = 3

        for i in range(0, len(points), points_per_slide):
            chunk = points[i:i + points_per_slide]
            if chunk:
                slides.append({
                    "type": "content",
                    "title": title,
                    "subtitle": f"({i // points_per_slide + 1})" if len(points) > points_per_slide else "",
                    "content": '\n'.join(chunk)
                })

        if not slides:
            slides.append({
                "type": "content",
                "title": title,
                "subtitle": "",
                "content": content
            })

        return slides

    def _parse_bullet_points(self, content: str) -> List[str]:
        """解析bullet points"""
        if not content:
            return []

        lines = content.split('\n')
        points = []
        for line in lines:
            line = line.strip()
            if line:
                if not line.startswith('•') and not line.startswith('-') and not line.startswith('*'):
                    line = '• ' + line
                points.append(line)

        return points if points else [content]

    def _generate_slide_html(self, slide: Dict[str, Any], config: Dict[str, Any]) -> str:
        """生成单个幻灯片的HTML"""
        slide_type = slide.get("type", "content")
        title = slide.get("title", "")
        subtitle = slide.get("subtitle", "")
        content = slide.get("content", "")

        if slide_type == "title":
            return f'<div class="slide title-slide"><h1>{title}</h1><h3>{subtitle}</h3></div>'
        elif slide_type == "agenda":
            return f'<div class="slide agenda-slide"><h2>{title}</h2><div class="content">{content}</div></div>'
        elif slide_type == "thankyou":
            return f'<div class="slide thankyou-slide"><h2>{title}</h2><h3>{subtitle}</h3></div>'
        else:
            return f'''<div class="slide content-slide">
                <h2>{title}</h2>
                {f'<h3>{subtitle}</h3>' if subtitle else ''}
                <div class="content">{content}</div>
            </div>'''

    def _generate_css_styles(self, config: Dict[str, Any]) -> str:
        """生成CSS样式"""
        return f"""
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: {config['font_family']};
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .presentation-container {{
            width: 1280px;
            height: 720px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
            margin: 0 auto;
        }}
        .slides-wrapper {{
            position: relative;
            width: 100%;
            height: 100%;
            overflow: hidden;
        }}
        .slide {{
            display: none;
            padding: 80px;
            width: 100%;
            height: 100%;
            background: white;
            flex-direction: column;
        }}
        .slide.active {{ display: flex; }}
        .slide.title-slide {{
            background: linear-gradient(135deg, {config['color_scheme']} 0%, {config['color_scheme']} 100%);
            color: white;
            justify-content: center;
            align-items: center;
        }}
        .slide.title-slide h1 {{
            font-size: 3em;
            margin-bottom: 20px;
            color: white;
        }}
        .slide h1 {{ font-size: 2.5em; margin-bottom: 30px; color: {config['color_scheme']}; }}
        .slide h2 {{ font-size: 2em; margin-bottom: 20px; color: {config['color_scheme']}; }}
        .slide h3 {{ font-size: 1.2em; color: #666; margin-bottom: 15px; }}
        .slide .content {{
            font-size: 1.1em;
            line-height: 1.8;
            color: #333;
            white-space: pre-line;
        }}
        .slide.agenda-slide {{ background: #f8f9fa; }}
        .slide.thankyou-slide {{
            background: linear-gradient(135deg, {config['color_scheme']} 0%, #764ba2 100%);
            color: white;
            justify-content: center;
            align-items: center;
        }}
        .slide.thankyou-slide h2 {{ color: white; font-size: 3em; }}
        .slide.thankyou-slide h3 {{ color: rgba(255,255,255,0.9); }}
        .navigation {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            gap: 20px;
            background: white;
            padding: 10px 30px;
            border-radius: 50px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        .navigation button {{
            padding: 10px 20px;
            border: none;
            background: {config['color_scheme']};
            color: white;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s;
        }}
        .navigation button:hover {{
            background: #764ba2;
            transform: scale(1.05);
        }}
        .navigation span {{
            font-size: 1.1em;
            color: #333;
            font-weight: bold;
        }}
        """

ppt_service = PPTService()
