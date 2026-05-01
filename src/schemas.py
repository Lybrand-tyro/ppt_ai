"""
Pydantic 请求模型
"""

from pydantic import BaseModel, Field
from typing import Optional


class LLMConfigRequest(BaseModel):
    api_endpoint: str = Field(..., description="API端点")
    api_key: str = Field("", description="API密钥")
    model_name: str = Field("gpt-3.5-turbo", description="模型名称")
    is_local: bool = Field(False, description="是否为本地模型")


class WebSearchConfigRequest(BaseModel):
    provider: str = Field(..., description="搜索引擎类型(tavily/serpapi/bing/google/brave)")
    api_key: str = Field("", description="API密钥")
    cx: Optional[str] = Field(None, description="Google自定义搜索CX")


class WebSearchRequest(BaseModel):
    query: str = Field(..., description="搜索查询")
    max_results: int = Field(5, description="最大结果数")


class GenerateOutlineRequest(BaseModel):
    topic: str = Field(..., description="PPT主题")
    language: str = Field("zh", description="语言(zh/en)")
    use_web_search: bool = Field(False, description="是否使用联网搜索")
    task_id: str = Field("", description="进度跟踪任务ID")


class GenerateSlidesRequest(BaseModel):
    outline: dict = Field(..., description="大纲数据")
    scenario: str = Field("general", description="场景(general/technology/business/education/tourism/science)")
    use_llm: bool = Field(False, description="是否使用LLM")
    use_web_search: bool = Field(False, description="是否使用联网搜索")
    task_id: str = Field("", description="进度跟踪任务ID")


class DownloadPptxRequest(BaseModel):
    outline: dict = Field(..., description="大纲数据")
    scenario: str = Field("general", description="场景")
    use_llm: bool = Field(False, description="是否使用LLM")
    use_web_search: bool = Field(False, description="是否使用联网搜索")
    task_id: str = Field("", description="进度跟踪任务ID")


class AdminLoginRequest(BaseModel):
    password: str = Field(..., description="管理员密码")


class AdminSetPasswordRequest(BaseModel):
    password: str = Field(..., description="新密码")


class HistoryApplyRequest(BaseModel):
    index: int = Field(..., description="历史记录索引")


class CancelRequest(BaseModel):
    pass
