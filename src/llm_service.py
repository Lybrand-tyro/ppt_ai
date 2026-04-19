"""
LLM服务模块
支持本地模型（如WSL2 llama.cpp）和OpenAI兼容的云端API
"""

from typing import Dict, Any, Optional, List
import requests
import json
from .logger import logger

class LLMService:
    """大语言模型服务"""

    def __init__(self):
        self.config: Dict[str, Any] = {
            "api_endpoint": "",
            "api_key": "",
            "model_name": "gpt-3.5-turbo",
            "is_local": False
        }
        self.is_configured = False

    def configure(self, api_endpoint: str, api_key: str, model_name: str, is_local: bool = False):
        """配置LLM服务

        Args:
            api_endpoint: API端点（如 http://localhost:8080/v1/chat/completions）
            api_key: API密钥
            model_name: 模型名称
            is_local: 是否为本地模型
        """
        self.config = {
            "api_endpoint": api_endpoint,
            "api_key": api_key,
            "model_name": model_name,
            "is_local": is_local
        }
        self.is_configured = bool(api_endpoint)
        logger.info(f"LLM服务已配置: endpoint={api_endpoint}, model={model_name}, is_local={is_local}")

    def generate_outline(self, topic: str, language: str = "zh") -> Dict[str, Any]:
        """使用LLM生成PPT大纲

        Args:
            topic: PPT主题/用户需求
            language: 语言（zh/en）

        Returns:
            大纲数据字典
        """
        if not self.is_configured:
            logger.warning("LLM服务未配置，使用模板生成大纲")
            return self._generate_template_outline(topic, language)

        logger.info(f"使用LLM生成大纲: topic={topic}, language={language}")

        prompt = self._build_outline_prompt(topic, language)

        try:
            response = self._call_llm(prompt)
            outline = self._parse_outline_response(response)
            logger.info(f"LLM生成大纲成功: {len(outline.get('slides', []))} 张幻灯片")
            return outline
        except Exception as e:
            logger.error(f"LLM生成大纲失败: {e}")
            logger.info("回退到模板生成大纲")
            return self._generate_template_outline(topic, language)

    def generate_content(self, slide_title: str, slide_type: str, topic: str, language: str = "zh") -> str:
        """使用LLM生成幻灯片内容

        Args:
            slide_title: 幻灯片标题
            slide_type: 幻灯片类型
            topic: PPT主题
            language: 语言

        Returns:
            生成的内容文本
        """
        if not self.is_configured:
            logger.warning("LLM服务未配置，使用模板生成内容")
            return self._generate_template_content(slide_title, topic)

        logger.info(f"使用LLM生成内容: title={slide_title}, type={slide_type}")

        prompt = self._build_content_prompt(slide_title, slide_type, topic, language)

        try:
            response = self._call_llm(prompt)
            content = self._parse_content_response(response)
            logger.info(f"LLM生成内容成功: {len(content)} 字符")
            return content
        except Exception as e:
            logger.error(f"LLM生成内容失败: {e}")
            logger.info("回退到模板生成内容")
            return self._generate_template_content(slide_title, topic)

    def _build_outline_prompt(self, topic: str, language: str) -> str:
        """构建大纲生成提示词"""
        if language == "zh":
            return f"""请生成PPT大纲：

用户需求：{topic}

**重要要求：**
1. 直接生成最终结果，不要包含任何思考过程、草稿或中间步骤
2. 严格控制幻灯片数量在6-10页之间
3. 只返回JSON格式，不要包含其他任何文字
4. 确保JSON格式完全正确，可直接解析

请按照以下JSON格式返回PPT大纲：
{{
    "title": "PPT标题",
    "slides": [
        {{"id": 1, "type": "title", "title": "标题", "subtitle": "副标题", "content": ""}},
        {{"id": 2, "type": "agenda", "title": "目录", "subtitle": "", "content": "目录内容"}},
        {{"id": 3, "type": "content", "title": "第一部分标题", "subtitle": "", "content": "内容要点"}},
        ...更多内容幻灯片...
        {{"id": N, "type": "thankyou", "title": "谢谢", "subtitle": "感谢语", "content": ""}}
    ],
    "metadata": {{"language": "{language}", "total_slides": N}}
}}"""
        else:
            return f"""Generate PPT outline:

User requirements: {topic}

**Important Requirements:**
1. Generate the final result directly, no thinking process, draft, or intermediate steps
2. Strictly control the number of slides between 6-10
3. Only return JSON format, no other text
4. Ensure the JSON format is completely correct and directly parseable

Please return the PPT outline in the following JSON format:
{{
    "title": "PPT Title",
    "slides": [
        {{"id": 1, "type": "title", "title": "Title", "subtitle": "Subtitle", "content": ""}},
        {{"id": 2, "type": "agenda", "title": "Agenda", "subtitle": "", "content": "Agenda content"}},
        {{"id": 3, "type": "content", "title": "Section 1 Title", "subtitle": "", "content": "Content points"}},
        ...more content slides...
        {{"id": N, "type": "thankyou", "title": "Thank You", "subtitle": "Thank you message", "content": ""}}
    ],
    "metadata": {{"language": "{language}", "total_slides": N}}
}}"""

    def _build_content_prompt(self, slide_title: str, slide_type: str, topic: str, language: str) -> str:
        """构建内容生成提示词"""
        if language == "zh":
            return f"""请为以下幻灯片生成详细内容：
幻灯片标题：{slide_title}
幻灯片类型：{slide_type}
PPT主题：{topic}

**重要要求：**
1. 直接生成最终结果，不要包含任何思考过程、草稿或中间步骤
2. 只返回bullet point格式的内容，不要其他文字
3. 内容要专业、有深度、符合演示场景
4. 生成3-5个具体的要点内容，使用简洁的bullet point格式（每个要点以"• "开头）"""
        else:
            return f"""Please generate detailed content for the following slide:
Slide Title: {slide_title}
Slide Type: {slide_type}
PPT Topic: {topic}

**Important Requirements:**
1. Generate the final result directly, no thinking process, draft, or intermediate steps
2. Only return bullet point content, no other text
3. Content should be professional, in-depth, and appropriate for the presentation scenario
4. Please generate 3-5 specific content points in a concise bullet point format (each point starts with "• ")"""

    def _call_llm(self, prompt: str) -> str:
        """调用LLM API

        Args:
            prompt: 提示词

        Returns:
            LLM返回的文本
        """
        logger.debug(f"调用LLM API: endpoint={self.config['api_endpoint']}")

        headers = {
            "Content-Type": "application/json"
        }
        if self.config["api_key"]:
            headers["Authorization"] = f"Bearer {self.config['api_key']}"

        payload = {
            "model": self.config["model_name"],
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        if self.config["is_local"]:
            payload["stream"] = False

        try:
            response = requests.post(
                self.config["api_endpoint"],
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            elif "content" in result:
                return result["content"]
            else:
                raise ValueError(f"Unexpected response format: {result}")

        except requests.exceptions.Timeout:
            logger.error("LLM API调用超时")
            raise TimeoutError("LLM API调用超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM API调用失败: {e}")
            raise

    def _parse_outline_response(self, response: str) -> Dict[str, Any]:
        """解析大纲响应"""
        try:
            json_str = self._extract_json(response)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            raise ValueError(f"无法解析LLM返回的大纲数据: {e}")

    def _parse_content_response(self, response: str) -> str:
        """解析内容响应"""
        content = response.strip()
        if not content:
            raise ValueError("LLM返回的内容为空")
        return content

    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON字符串"""
        text = text.strip()

        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx == -1 or end_idx == -1:
            raise ValueError("未找到JSON对象")

        return text[start_idx:end_idx+1]

    def _generate_template_outline(self, topic: str, language: str = "zh") -> Dict[str, Any]:
        """生成模板大纲（当LLM不可用时）"""
        logger.info(f"使用模板生成大纲: topic={topic}")

        if language == "zh":
            slides = [
                {"id": 1, "type": "title", "title": topic, "subtitle": "专业PPT演示", "content": ""},
                {"id": 2, "type": "agenda", "title": "目录", "subtitle": "", "content": "引言\n主要内容\n案例分析\n总结"},
                {"id": 3, "type": "content", "title": "引言", "subtitle": "", "content": f"• {topic}的定义与背景\n• {topic}的发展历程\n• 为什么关注{topic}"},
                {"id": 4, "type": "content", "title": "主要内容", "subtitle": "", "content": f"• {topic}的核心要素\n• {topic}的主要特征\n• {topic}的应用场景"},
                {"id": 5, "type": "content", "title": "案例分析", "subtitle": "", "content": f"• 成功的{topic}案例\n• 案例中的关键成功因素\n• 可借鉴的经验与教训"},
                {"id": 6, "type": "thankyou", "title": "谢谢", "subtitle": "感谢您的聆听", "content": ""}
            ]
        else:
            slides = [
                {"id": 1, "type": "title", "title": topic, "subtitle": "Professional Presentation", "content": ""},
                {"id": 2, "type": "agenda", "title": "Agenda", "subtitle": "", "content": "Introduction\nMain Content\nCase Study\nConclusion"},
                {"id": 3, "type": "content", "title": "Introduction", "subtitle": "", "content": f"• Definition and background of {topic}\n• Development history of {topic}\n• Why we care about {topic}"},
                {"id": 4, "type": "content", "title": "Main Content", "subtitle": "", "content": f"• Core elements of {topic}\n• Main features of {topic}\n• Application scenarios of {topic}"},
                {"id": 5, "type": "content", "title": "Case Study", "subtitle": "", "content": f"• Successful {topic} cases\n• Key success factors in cases\n• Lessons learned"},
                {"id": 6, "type": "thankyou", "title": "Thank You", "subtitle": "Thanks for listening", "content": ""}
            ]

        return {
            "title": topic,
            "slides": slides,
            "metadata": {
                "scenario": "general",
                "language": language,
                "total_slides": len(slides)
            }
        }

    def _generate_template_content(self, slide_title: str, topic: str) -> str:
        """生成模板内容（当LLM不可用时）"""
        templates = {
            "引言": f"• {topic}的定义与背景\n• {topic}的发展历程\n• 为什么关注{topic}",
            "主要内容": f"• {topic}的核心要素\n• {topic}的主要特征\n• {topic}的应用场景",
            "案例分析": f"• 成功的{topic}案例\n• 案例中的关键成功因素\n• 可借鉴的经验与教训",
            "总结": f"• {topic}的核心观点总结\n• 未来发展趋势展望\n• 行动建议与下一步"
        }

        return templates.get(slide_title, f"• 关于{topic}的重要内容\n• {topic}的关键点\n• {topic}的实际应用")

llm_service = LLMService()
