"""
联网搜索服务模块
策略模式：多种搜索引擎 Provider + 统一入口 WebSearchService
"""

from typing import Dict, Any
from abc import ABC, abstractmethod
import requests
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
