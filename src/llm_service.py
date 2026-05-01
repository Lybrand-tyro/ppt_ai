"""
LLM服务模块
支持本地模型（如WSL2 llama.cpp）和OpenAI兼容的云端API
支持多种联网搜索API，丰富内容生成
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import requests
import json
from .logger import logger


class WebSearchProvider(ABC):
    """联网搜索提供者基类"""

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def configure(self, **kwargs):
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        pass

    def search_for_content(self, query: str, language: str = "zh") -> str:
        if not self.is_configured():
            return ""

        result = self.search(query, max_results=3)

        if result.get("answer"):
            return result["answer"]

        contents = []
        for r in result.get("results", []):
            if r.get("content"):
                contents.append(r["content"])
        return "\n".join(contents)


class TavilySearchProvider(WebSearchProvider):
    """Tavily搜索提供者"""

    def __init__(self):
        self._api_key: str = ""
        self._is_configured: bool = False
        self.base_url = "https://api.tavily.com"

    def get_name(self) -> str:
        return "Tavily"

    def configure(self, **kwargs):
        api_key = kwargs.get("api_key", "")
        self._api_key = api_key
        self._is_configured = bool(api_key)
        logger.info(f"Tavily搜索服务已配置: api_key={'***' + api_key[-4:] if len(api_key) > 4 else '***'}")

    def is_configured(self) -> bool:
        return self._is_configured

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        if not self._is_configured:
            return {"results": [], "answer": ""}

        logger.info(f"Tavily搜索: query={query}, max_results={max_results}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}"
        }

        payload = {
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_images": False,
            "include_answer": True,
            "topic": "general"
        }

        try:
            response = requests.post(
                f"{self.base_url}/search",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Tavily搜索成功: {len(result.get('results', []))} 条结果")
            return result
        except requests.exceptions.Timeout:
            logger.error("Tavily搜索超时")
            return {"results": [], "answer": "", "error": "搜索超时"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Tavily搜索失败: {e}")
            return {"results": [], "answer": "", "error": str(e)}


class SerpAPISearchProvider(WebSearchProvider):
    """SerpAPI搜索提供者 (https://serpapi.com)"""

    def __init__(self):
        self._api_key: str = ""
        self._is_configured: bool = False

    def get_name(self) -> str:
        return "SerpAPI"

    def configure(self, **kwargs):
        api_key = kwargs.get("api_key", "")
        self._api_key = api_key
        self._is_configured = bool(api_key)
        logger.info(f"SerpAPI搜索服务已配置: api_key={'***' + api_key[-4:] if len(api_key) > 4 else '***'}")

    def is_configured(self) -> bool:
        return self._is_configured

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        if not self._is_configured:
            return {"results": [], "answer": ""}

        logger.info(f"SerpAPI搜索: query={query}, max_results={max_results}")

        try:
            response = requests.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": self._api_key,
                    "engine": "google",
                    "num": max_results,
                    "hl": "zh-cn"
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic_results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "content": item.get("snippet", "")
                })

            answer = data.get("answer_box", {}).get("snippet", "")
            if not answer and data.get("knowledge_graph", {}):
                answer = data.get("knowledge_graph", {}).get("description", "")

            logger.info(f"SerpAPI搜索成功: {len(results)} 条结果")
            return {"results": results, "answer": answer}
        except requests.exceptions.Timeout:
            logger.error("SerpAPI搜索超时")
            return {"results": [], "answer": "", "error": "搜索超时"}
        except requests.exceptions.RequestException as e:
            logger.error(f"SerpAPI搜索失败: {e}")
            return {"results": [], "answer": "", "error": str(e)}


class BingSearchProvider(WebSearchProvider):
    """Bing搜索提供者 (Azure Bing Search API v7)"""

    def __init__(self):
        self._api_key: str = ""
        self._is_configured: bool = False

    def get_name(self) -> str:
        return "Bing"

    def configure(self, **kwargs):
        api_key = kwargs.get("api_key", "")
        self._api_key = api_key
        self._is_configured = bool(api_key)
        logger.info(f"Bing搜索服务已配置: api_key={'***' + api_key[-4:] if len(api_key) > 4 else '***'}")

    def is_configured(self) -> bool:
        return self._is_configured

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        if not self._is_configured:
            return {"results": [], "answer": ""}

        logger.info(f"Bing搜索: query={query}, max_results={max_results}")

        try:
            response = requests.get(
                "https://api.bing.microsoft.com/v7.0/search",
                headers={"Ocp-Apim-Subscription-Key": self._api_key},
                params={"q": query, "count": max_results, "mkt": "zh-CN"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("webPages", {}).get("value", [])[:max_results]:
                results.append({
                    "title": item.get("name", ""),
                    "url": item.get("url", ""),
                    "content": item.get("snippet", "")
                })

            answer = ""
            if data.get("entities", {}).get("value"):
                answer = data["entities"]["value"][0].get("description", "")

            logger.info(f"Bing搜索成功: {len(results)} 条结果")
            return {"results": results, "answer": answer}
        except requests.exceptions.Timeout:
            logger.error("Bing搜索超时")
            return {"results": [], "answer": "", "error": "搜索超时"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Bing搜索失败: {e}")
            return {"results": [], "answer": "", "error": str(e)}


class GoogleSearchProvider(WebSearchProvider):
    """Google Custom Search提供者 (Programmable Search Engine)"""

    def __init__(self):
        self._api_key: str = ""
        self._cx: str = ""
        self._is_configured: bool = False

    def get_name(self) -> str:
        return "Google"

    def configure(self, **kwargs):
        api_key = kwargs.get("api_key", "")
        cx = kwargs.get("cx", "")
        self._api_key = api_key
        self._cx = cx
        self._is_configured = bool(api_key and cx)
        logger.info(f"Google搜索服务已配置: api_key={'***' + api_key[-4:] if len(api_key) > 4 else '***'}")

    def is_configured(self) -> bool:
        return self._is_configured

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        if not self._is_configured:
            return {"results": [], "answer": ""}

        logger.info(f"Google搜索: query={query}, max_results={max_results}")

        try:
            response = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": self._api_key,
                    "cx": self._cx,
                    "q": query,
                    "num": min(max_results, 10),
                    "hl": "zh-CN"
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("items", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "content": item.get("snippet", "")
                })

            answer = ""
            if data.get("knowledgeGraph"):
                answer = data["knowledgeGraph"].get("description", "")

            logger.info(f"Google搜索成功: {len(results)} 条结果")
            return {"results": results, "answer": answer}
        except requests.exceptions.Timeout:
            logger.error("Google搜索超时")
            return {"results": [], "answer": "", "error": "搜索超时"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Google搜索失败: {e}")
            return {"results": [], "answer": "", "error": str(e)}


class BraveSearchProvider(WebSearchProvider):
    """Brave搜索提供者 (https://brave.com/search/api/)"""

    def __init__(self):
        self._api_key: str = ""
        self._is_configured: bool = False

    def get_name(self) -> str:
        return "Brave"

    def configure(self, **kwargs):
        api_key = kwargs.get("api_key", "")
        self._api_key = api_key
        self._is_configured = bool(api_key)
        logger.info(f"Brave搜索服务已配置: api_key={'***' + api_key[-4:] if len(api_key) > 4 else '***'}")

    def is_configured(self) -> bool:
        return self._is_configured

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        if not self._is_configured:
            return {"results": [], "answer": ""}

        logger.info(f"Brave搜索: query={query}, max_results={max_results}")

        try:
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": self._api_key
                },
                params={
                    "q": query,
                    "count": max_results,
                    "search_lang": "zh-hans"
                },
                timeout=20
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("web", {}).get("results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("description", "")
                })

            answer = ""
            if data.get("query", {}).get("show_strict_def"):
                answer = data["query"]["show_strict_def"]

            logger.info(f"Brave搜索成功: {len(results)} 条结果")
            return {"results": results, "answer": answer}
        except requests.exceptions.Timeout:
            logger.error("Brave搜索超时")
            return {"results": [], "answer": "", "error": "搜索超时"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Brave搜索失败: {e}")
            return {"results": [], "answer": "", "error": str(e)}


class WebSearchService:
    """联网搜索服务（统一入口）"""

    PROVIDERS = {
        "tavily": TavilySearchProvider,
        "serpapi": SerpAPISearchProvider,
        "bing": BingSearchProvider,
        "google": GoogleSearchProvider,
        "brave": BraveSearchProvider,
    }

    def __init__(self):
        self._providers: Dict[str, WebSearchProvider] = {}
        self._active_provider: str = ""
        for key, cls in self.PROVIDERS.items():
            self._providers[key] = cls()

    @property
    def active_provider(self) -> str:
        return self._active_provider

    def configure_provider(self, provider_key: str, **kwargs) -> bool:
        if provider_key not in self._providers:
            logger.error(f"未知的搜索引擎: {provider_key}")
            return False

        self._providers[provider_key].configure(**kwargs)
        if self._providers[provider_key].is_configured():
            self._active_provider = provider_key
            logger.info(f"活跃搜索引擎切换为: {provider_key}")
        return True

    def is_configured(self) -> bool:
        return bool(self._active_provider) and self._providers[self._active_provider].is_configured()

    def get_active_provider_name(self) -> str:
        if self._active_provider:
            return self._providers[self._active_provider].get_name()
        return ""

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        if not self.is_configured():
            logger.warning("联网搜索服务未配置")
            return {"results": [], "answer": ""}

        return self._providers[self._active_provider].search(query, max_results)

    def search_for_content(self, slide_title: str, topic: str, language: str = "zh") -> str:
        if not self.is_configured():
            return ""

        if language == "zh":
            query = f"{topic} {slide_title} 介绍 分析"
        else:
            query = f"{topic} {slide_title} introduction analysis"

        provider = self._providers[self._active_provider]
        return provider.search_for_content(query, language)

    def get_provider_status(self) -> Dict[str, Any]:
        status = {}
        for key, provider in self._providers.items():
            status[key] = {
                "name": provider.get_name(),
                "is_configured": provider.is_configured(),
                "is_active": key == self._active_provider
            }
        return status


web_search_service = WebSearchService()


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

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        """自动补全API端点路径"""
        endpoint = endpoint.strip().rstrip('/')
        if not endpoint:
            return endpoint
        if endpoint.endswith('/v1/chat/completions'):
            return endpoint
        if endpoint.endswith('/v1'):
            return endpoint + '/chat/completions'
        return endpoint + '/v1/chat/completions'

    def configure(self, api_endpoint: str, api_key: str, model_name: str, is_local: bool = False):
        """配置LLM服务

        Args:
            api_endpoint: API端点（如 http://localhost:18080 或 http://localhost:18080/v1/chat/completions）
            api_key: API密钥
            model_name: 模型名称
            is_local: 是否为本地模型
        """
        api_endpoint = self._normalize_endpoint(api_endpoint)
        self.config = {
            "api_endpoint": api_endpoint,
            "api_key": api_key,
            "model_name": model_name,
            "is_local": is_local
        }
        self.is_configured = bool(api_endpoint)
        logger.info(f"LLM服务已配置: endpoint={api_endpoint}, model={model_name}, is_local={is_local}")

    def generate_outline(self, topic: str, language: str = "zh", use_web_search: bool = False, task_id: str = "") -> Dict[str, Any]:
        """使用LLM生成PPT大纲

        Args:
            topic: PPT主题/用户需求
            language: 语言（zh/en）
            use_web_search: 是否使用联网搜索增强
            task_id: 进度跟踪任务ID

        Returns:
            大纲数据字典
        """
        from .progress import progress_tracker

        if not self.is_configured:
            logger.warning("LLM服务未配置，使用模板生成大纲")
            return self._generate_template_outline(topic, language)

        logger.info(f"使用LLM生成大纲: topic={topic}, language={language}, use_web_search={use_web_search}")

        web_context = ""
        if use_web_search and web_search_service.is_configured():
            if task_id and progress_tracker.is_cancelled(task_id):
                return self._generate_template_outline(topic, language)
            progress_tracker.update(task_id, 10, "🔍 联网搜索参考资料...", "web_search_outline")
            logger.info("联网搜索增强大纲生成...")
            web_context = web_search_service.search_for_content(topic, topic, language)
            if web_context:
                logger.info(f"联网搜索获取到上下文: {len(web_context)} 字符")
                progress_tracker.update(task_id, 25, f"✅ 搜索完成，获取到 {len(web_context)} 字符资料", "web_search_done")

        if task_id and progress_tracker.is_cancelled(task_id):
            return self._generate_template_outline(topic, language)

        progress_tracker.update(task_id, 30, "📝 构建提示词，请求LLM生成大纲...", "llm_request_outline")
        prompt = self._build_outline_prompt(topic, language, web_context)

        try:
            progress_tracker.update(task_id, 40, "⏳ 等待LLM响应（生成大纲）...", "llm_waiting_outline")
            response = self._call_llm(prompt, task_id)
            if task_id and progress_tracker.is_cancelled(task_id):
                return self._generate_template_outline(topic, language)
            progress_tracker.update(task_id, 80, "📋 解析LLM返回的大纲...", "parse_outline")
            outline = self._parse_outline_response(response)
            logger.info(f"LLM生成大纲成功: {len(outline.get('slides', []))} 张幻灯片")
            return outline
        except Exception as e:
            logger.error(f"LLM生成大纲失败: {e}")
            logger.info("回退到模板生成大纲")
            return self._generate_template_outline(topic, language)

    def generate_content(self, slide_title: str, slide_type: str, topic: str, language: str = "zh", use_web_search: bool = False, task_id: str = "") -> str:
        """使用LLM生成幻灯片内容

        Args:
            slide_title: 幻灯片标题
            slide_type: 幻灯片类型
            topic: PPT主题
            language: 语言
            use_web_search: 是否使用联网搜索增强
            task_id: 进度跟踪任务ID

        Returns:
            生成的内容文本
        """
        from .progress import progress_tracker

        if not self.is_configured:
            logger.warning("LLM服务未配置，使用模板生成内容")
            return self._generate_template_content(slide_title, topic)

        logger.info(f"使用LLM生成内容: title={slide_title}, type={slide_type}, use_web_search={use_web_search}")

        web_context = ""
        if use_web_search and web_search_service.is_configured():
            if task_id and progress_tracker.is_cancelled(task_id):
                return self._generate_template_content(slide_title, topic)
            progress_tracker.update(task_id, -1, f"🔍 搜索「{slide_title}」相关资料...", f"web_search_{slide_title}")
            logger.info(f"联网搜索增强内容生成: {slide_title}")
            web_context = web_search_service.search_for_content(slide_title, topic, language)
            if web_context:
                logger.info(f"联网搜索获取到上下文: {len(web_context)} 字符")

        if task_id and progress_tracker.is_cancelled(task_id):
            return self._generate_template_content(slide_title, topic)

        prompt = self._build_content_prompt(slide_title, slide_type, topic, language, web_context)

        try:
            response = self._call_llm(prompt, task_id)
            if task_id and progress_tracker.is_cancelled(task_id):
                return self._generate_template_content(slide_title, topic)
            content = self._parse_content_response(response)
            logger.info(f"LLM生成内容成功: {len(content)} 字符")
            return content
        except Exception as e:
            logger.error(f"LLM生成内容失败: {e}")
            logger.info("回退到模板生成内容")
            return self._generate_template_content(slide_title, topic)

    def _build_outline_prompt(self, topic: str, language: str, web_context: str = "") -> str:
        """构建大纲生成提示词"""
        web_context_section = ""
        if web_context:
            if language == "zh":
                web_context_section = f"""

**联网搜索参考资料（请结合以下信息生成更丰富、准确的大纲）：**
{web_context}
"""
            else:
                web_context_section = f"""

**Web Search Reference (please incorporate the following information to create a richer, more accurate outline):**
{web_context}
"""

        if language == "zh":
            return f"""请生成PPT大纲：

用户需求：{topic}
{web_context_section}
**重要要求：**
1. 直接生成最终结果，不要包含任何思考过程、草稿或中间步骤
2. 严格控制幻灯片数量在6-10页之间
3. 只返回JSON格式，不要包含其他任何文字
4. 确保JSON格式完全正确，可直接解析
{"5. 结合联网搜索资料，使内容更加丰富、准确、有深度" if web_context else ""}

**样式设计要求：**
每张幻灯片需要包含style字段，用于指导视觉呈现：
- layout: 布局方式
  - "centered" = 内容居中展示，适合要点少、强调冲击力的页面
  - "left" = 左对齐常规布局，适合要点较多的页面
  - "two-column" = 双栏布局，适合对比或分类内容
  - "quote" = 大字引用布局，适合核心观点/金句
  - "cards" = 卡片式布局，适合并列的3-4个模块
  - "timeline" = 时间线布局，适合发展历程/步骤流程
- accent_color: 该页强调色（十六进制），根据内容主题选择，如科技用蓝色#3498DB、环保用绿色#27AE60、警示用红色#E74C3C等
- icon: 代表该页主题的emoji图标，如🤖🚀💡📊🔬🌍等
- content_style: 内容呈现形式
  - "bullet" = 常规要点列表
  - "numbered" = 编号列表，适合步骤/排名
  - "highlight" = 突出关键词，适合核心概念

请按照以下JSON格式返回PPT大纲：
{{
    "title": "PPT标题",
    "slides": [
        {{"id": 1, "type": "title", "title": "标题", "subtitle": "副标题", "content": "", "style": {{"layout": "centered", "accent_color": "#3498DB", "icon": "🚀"}}}},
        {{"id": 2, "type": "agenda", "title": "目录", "subtitle": "", "content": "目录内容", "style": {{"layout": "left", "accent_color": "#3498DB", "icon": "📋"}}}},
        {{"id": 3, "type": "content", "title": "第一部分标题", "subtitle": "", "content": "内容要点", "style": {{"layout": "left", "accent_color": "#3498DB", "icon": "💡", "content_style": "bullet"}}}},
        {{"id": 4, "type": "content", "title": "发展历程", "subtitle": "", "content": "历程内容", "style": {{"layout": "timeline", "accent_color": "#E67E22", "icon": "📅", "content_style": "numbered"}}}},
        {{"id": 5, "type": "content", "title": "核心观点", "subtitle": "", "content": "观点内容", "style": {{"layout": "quote", "accent_color": "#9B59B6", "icon": "💬", "content_style": "highlight"}}}},
        {{"id": 6, "type": "content", "title": "分类对比", "subtitle": "", "content": "对比内容", "style": {{"layout": "two-column", "accent_color": "#27AE60", "icon": "⚖️", "content_style": "bullet"}}}},
        ...更多内容幻灯片...
        {{"id": N, "type": "thankyou", "title": "谢谢", "subtitle": "感谢语", "content": "", "style": {{"layout": "centered", "accent_color": "#3498DB", "icon": "🙏"}}}}
    ],
    "metadata": {{"language": "{language}", "total_slides": N}}
}}"""
        else:
            return f"""Generate PPT outline:

User requirements: {topic}
{web_context_section}
**Important Requirements:**
1. Generate the final result directly, no thinking process, draft, or intermediate steps
2. Strictly control the number of slides between 6-10
3. Only return JSON format, no other text
4. Ensure the JSON format is completely correct and directly parseable
{"5. Incorporate web search information to make the content richer, more accurate, and more in-depth" if web_context else ""}

**Style Design Requirements:**
Each slide must include a "style" field to guide visual presentation:
- layout: layout type
  - "centered" = centered content, ideal for impact with few points
  - "left" = standard left-aligned layout, ideal for many points
  - "two-column" = two-column layout, ideal for comparisons
  - "quote" = large quote layout, ideal for key insights/mottos
  - "cards" = card-style layout, ideal for 3-4 parallel modules
  - "timeline" = timeline layout, ideal for history/steps
- accent_color: page accent color (hex), choose based on content theme
- icon: emoji representing the slide topic
- content_style: content presentation form
  - "bullet" = standard bullet list
  - "numbered" = numbered list, ideal for steps/rankings
  - "highlight" = highlighted keywords, ideal for core concepts

Please return the PPT outline in the following JSON format:
{{
    "title": "PPT Title",
    "slides": [
        {{"id": 1, "type": "title", "title": "Title", "subtitle": "Subtitle", "content": "", "style": {{"layout": "centered", "accent_color": "#3498DB", "icon": "🚀"}}}},
        {{"id": 2, "type": "agenda", "title": "Agenda", "subtitle": "", "content": "Agenda content", "style": {{"layout": "left", "accent_color": "#3498DB", "icon": "📋"}}}},
        {{"id": 3, "type": "content", "title": "Section 1", "subtitle": "", "content": "Content", "style": {{"layout": "left", "accent_color": "#3498DB", "icon": "💡", "content_style": "bullet"}}}},
        {{"id": 4, "type": "content", "title": "History", "subtitle": "", "content": "History content", "style": {{"layout": "timeline", "accent_color": "#E67E22", "icon": "📅", "content_style": "numbered"}}}},
        {{"id": 5, "type": "content", "title": "Key Insight", "subtitle": "", "content": "Insight content", "style": {{"layout": "quote", "accent_color": "#9B59B6", "icon": "💬", "content_style": "highlight"}}}},
        ...more content slides...
        {{"id": N, "type": "thankyou", "title": "Thank You", "subtitle": "Thank you message", "content": "", "style": {{"layout": "centered", "accent_color": "#3498DB", "icon": "🙏"}}}}
    ],
    "metadata": {{"language": "{language}", "total_slides": N}}
}}"""

    def _build_content_prompt(self, slide_title: str, slide_type: str, topic: str, language: str, web_context: str = "") -> str:
        """构建内容生成提示词"""
        web_context_section = ""
        if web_context:
            if language == "zh":
                web_context_section = f"""

**联网搜索参考资料（请结合以下信息生成更丰富、准确的内容）：**
{web_context}
"""
            else:
                web_context_section = f"""

**Web Search Reference (please incorporate the following information to create richer, more accurate content):**
{web_context}
"""

        if language == "zh":
            return f"""请为以下幻灯片生成详细内容：
幻灯片标题：{slide_title}
幻灯片类型：{slide_type}
PPT主题：{topic}
{web_context_section}
**重要要求：**
1. 直接生成最终结果，不要包含任何思考过程、草稿或中间步骤
2. 只返回内容文本，不要其他文字
3. 内容要专业、有深度、符合演示场景
4. 生成3-5个具体的要点内容
5. 格式要求：
   - bullet样式：每个要点以"• "开头
   - numbered样式：每个要点以"1. ""2. ""3. "开头
   - highlight样式：每个要点用**加粗**标记关键词，格式为"• **关键词** 解释说明"
6. 如果要点中有特别重要的数据或结论，用**加粗**标记
{"7. 结合联网搜索资料，使内容更加丰富、准确、有深度，包含真实数据和案例" if web_context else ""}"""
        else:
            return f"""Please generate detailed content for the following slide:
Slide Title: {slide_title}
Slide Type: {slide_type}
PPT Topic: {topic}
{web_context_section}
**Important Requirements:**
1. Generate the final result directly, no thinking process, draft, or intermediate steps
2. Only return content text, no other text
3. Content should be professional, in-depth, and appropriate for the presentation scenario
4. Please generate 3-5 specific content points
5. Format requirements:
   - bullet style: each point starts with "• "
   - numbered style: each point starts with "1. " "2. " "3. "
   - highlight style: mark key terms with **bold**, format as "• **Key Term** explanation"
6. If any point contains important data or conclusions, mark them with **bold**
{"7. Incorporate web search information to make the content richer, more accurate, and more in-depth, including real data and cases" if web_context else ""}"""

    def _call_llm(self, prompt: str, task_id: str = "") -> str:
        """调用LLM API（流式响应，含重试机制和取消检查）

        Args:
            prompt: 提示词
            task_id: 进度跟踪任务ID

        Returns:
            LLM返回的文本
        """
        from .progress import progress_tracker
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
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": True
        }

        if self.config["is_local"]:
            payload["stream"] = False

        max_retries = 3
        connect_timeout = 30
        read_timeout = 300

        for attempt in range(max_retries):
            try:
                if task_id and progress_tracker.is_cancelled(task_id):
                    raise InterruptedError("任务已取消")
                logger.info(f"LLM API调用 (尝试 {attempt + 1}/{max_retries})")

                if not payload.get("stream", False):
                    response = requests.post(
                        self.config["api_endpoint"],
                        headers=headers,
                        json=payload,
                        timeout=(connect_timeout, read_timeout)
                    )
                    if response.status_code == 401:
                        logger.error("LLM API认证失败(401)：API密钥无效或已过期，请检查API Key")
                        raise PermissionError("API密钥无效或已过期，请检查LLM配置中的API Key")
                    if response.status_code == 403:
                        logger.error("LLM API访问被拒绝(403)：无权限访问该模型")
                        raise PermissionError("无权限访问该模型，请检查API Key权限")
                    if response.status_code == 404:
                        logger.error(f"LLM API端点不存在(404)：请检查端点地址和模型名称")
                        raise ValueError(f"API端点或模型不存在，请检查端点地址和模型名称是否正确")
                    response.raise_for_status()
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    elif "content" in result:
                        return result["content"]
                    else:
                        raise ValueError(f"Unexpected response format: {result}")

                response = requests.post(
                    self.config["api_endpoint"],
                    headers=headers,
                    json=payload,
                    timeout=(connect_timeout, read_timeout),
                    stream=True
                )

                if response.status_code == 401:
                    logger.error("LLM API认证失败(401)：API密钥无效或已过期，请检查API Key")
                    raise PermissionError("API密钥无效或已过期，请检查LLM配置中的API Key")
                if response.status_code == 403:
                    logger.error("LLM API访问被拒绝(403)：无权限访问该模型")
                    raise PermissionError("无权限访问该模型，请检查API Key权限")
                if response.status_code == 404:
                    logger.error(f"LLM API端点不存在(404)：请检查端点地址和模型名称")
                    raise ValueError(f"API端点或模型不存在，请检查端点地址和模型名称是否正确")
                response.raise_for_status()

                full_content = []
                for line in response.iter_lines(decode_unicode=True):
                    if task_id and progress_tracker.is_cancelled(task_id):
                        response.close()
                        raise InterruptedError("任务已取消")
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    full_content.append(content)
                        except json.JSONDecodeError:
                            continue

                response.close()
                result_text = "".join(full_content)
                if not result_text:
                    raise ValueError("LLM返回空响应")
                return result_text

            except (PermissionError, ValueError, InterruptedError):
                raise
            except requests.exceptions.Timeout:
                logger.warning(f"LLM API调用超时 (尝试 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    continue
                logger.error("LLM API调用超时，已达最大重试次数")
                raise TimeoutError(
                    f"LLM API调用超时（已重试{max_retries}次）。"
                    "可能原因：1)本地模型服务卡住，请重启llama.cpp；"
                    "2)模型推理速度慢，可尝试更小的模型；"
                    "3)网络问题，请检查API端点是否可达"
                )
            except requests.exceptions.RequestException as e:
                logger.error(f"LLM API调用失败: {e}")
                if attempt < max_retries - 1 and "ConnectionError" in type(e).__name__:
                    logger.info("连接错误，重试中...")
                    continue
                raise

        raise RuntimeError("LLM API调用异常终止")

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
