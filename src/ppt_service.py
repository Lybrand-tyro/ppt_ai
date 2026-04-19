"""
PPT生成服务模块
负责生成HTML和PPTX格式的PPT
"""

import io
from typing import Dict, Any, List
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
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

    def _hex_to_rgb(self, hex_color: str) -> RGBColor:
        """将十六进制颜色转换为RGBColor"""
        hex_color = hex_color.lstrip('#')
        return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))

    def generate_pptx(self, outline: Dict[str, Any], scenario: str = "general", use_llm: bool = False) -> bytes:
        """生成PPTX格式的PPT

        Args:
            outline: 大纲数据
            scenario: 应用场景
            use_llm: 是否使用LLM生成内容

        Returns:
            PPTX文件的字节数据
        """
        logger.info(f"开始生成PPTX: scenario={scenario}, use_llm={use_llm}")

        config = self.scenario_configs.get(scenario, self.scenario_configs["general"])
        color = self._hex_to_rgb(config["color_scheme"])
        topic = outline.get("title", "")
        language = outline.get("metadata", {}).get("language", "zh")

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        blank_layout = prs.slide_layouts[6]

        for slide_data in outline.get("slides", []):
            slide_type = slide_data.get("type", "content")
            title = slide_data.get("title", "")
            subtitle = slide_data.get("subtitle", "")
            content = slide_data.get("content", "")

            if slide_type == "content" and use_llm and llm_service.is_configured:
                try:
                    content = llm_service.generate_content(title, slide_type, topic, language)
                except Exception as e:
                    logger.error(f"LLM内容生成失败: {e}")

            slide = prs.slides.add_slide(blank_layout)

            if slide_type == "title":
                self._build_title_slide(slide, title, subtitle, color)
            elif slide_type == "agenda":
                self._build_agenda_slide(slide, title, content, color)
            elif slide_type == "thankyou":
                self._build_thankyou_slide(slide, title, subtitle, color)
            else:
                self._build_content_slide(slide, title, subtitle, content, color)

        buffer = io.BytesIO()
        prs.save(buffer)
        buffer.seek(0)
        pptx_bytes = buffer.read()

        logger.info(f"PPTX生成完成: {len(prs.slides)} 张幻灯片, {len(pptx_bytes)} 字节")
        return pptx_bytes

    def _build_title_slide(self, slide, title: str, subtitle: str, color: RGBColor):
        """构建标题幻灯片"""
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = color

        txBox = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(11.333), Inches(2))
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(44)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.alignment = PP_ALIGN.CENTER

        if subtitle:
            p2 = tf.add_paragraph()
            p2.text = subtitle
            p2.font.size = Pt(24)
            p2.font.color.rgb = RGBColor(230, 230, 230)
            p2.alignment = PP_ALIGN.CENTER

    def _build_agenda_slide(self, slide, title: str, content: str, color: RGBColor):
        """构建目录幻灯片"""
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(245, 245, 245)

        txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.2))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = color

        content_box = slide.shapes.add_textbox(Inches(1.5), Inches(2), Inches(10.333), Inches(4.5))
        tf2 = content_box.text_frame
        tf2.word_wrap = True

        lines = self._parse_bullet_points(content)
        for i, line in enumerate(lines):
            clean_line = line.lstrip('•-* ').strip()
            if i == 0:
                p = tf2.paragraphs[0]
            else:
                p = tf2.add_paragraph()
            p.text = clean_line
            p.font.size = Pt(22)
            p.font.color.rgb = RGBColor(51, 51, 51)
            p.space_after = Pt(12)
            p.level = 0

    def _build_thankyou_slide(self, slide, title: str, subtitle: str, color: RGBColor):
        """构建致谢幻灯片"""
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = color

        txBox = slide.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11.333), Inches(2))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(48)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.alignment = PP_ALIGN.CENTER

        if subtitle:
            p2 = tf.add_paragraph()
            p2.text = subtitle
            p2.font.size = Pt(24)
            p2.font.color.rgb = RGBColor(230, 230, 230)
            p2.alignment = PP_ALIGN.CENTER

    def _build_content_slide(self, slide, title: str, subtitle: str, content: str, color: RGBColor):
        """构建内容幻灯片"""
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(255, 255, 255)

        txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.2))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = color

        if subtitle:
            p2 = tf.add_paragraph()
            p2.text = subtitle
            p2.font.size = Pt(18)
            p2.font.color.rgb = RGBColor(128, 128, 128)

        content_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(11.333), Inches(4.5))
        tf2 = content_box.text_frame
        tf2.word_wrap = True

        lines = self._parse_bullet_points(content)
        for i, line in enumerate(lines):
            clean_line = line.lstrip('•-* ').strip()
            if i == 0:
                p = tf2.paragraphs[0]
            else:
                p = tf2.add_paragraph()
            p.text = "• " + clean_line
            p.font.size = Pt(20)
            p.font.color.rgb = RGBColor(51, 51, 51)
            p.space_after = Pt(10)

        left_line = slide.shapes.add_shape(
            1, Inches(0.4), Inches(0.5), Inches(0.06), Inches(1.0)
        )
        left_line.fill.solid()
        left_line.fill.fore_color.rgb = color
        left_line.line.fill.background()

ppt_service = PPTService()
