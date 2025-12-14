# tools/web_search.py
import os
import json
from typing import List, Dict, Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain.tools import tool
from tavily import TavilyClient
load_dotenv("properties.env")


class WebSearchArgs(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Max number of search results to return"
    )


# 为了避免每次调用都 new client，用一个简单的缓存
_tavily_client: TavilyClient | None = None


def _get_tavily_client() -> TavilyClient:
    global _tavily_client
    if _tavily_client is not None:
        return _tavily_client

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        # 这里不直接抛异常，在工具内部处理成 error JSON
        raise RuntimeError(
            "TAVILY_API_KEY is not set. "
            "Please export TAVILY_API_KEY in your environment."
        )

    _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


@tool(args_schema=WebSearchArgs)
def web_search(query: str, max_results: int = 5) -> str:
    """
    Real web search via Tavily. Returns JSON list[{title, url, snippet}].

    - query: free-text search query
    - max_results: number of results to request from Tavily

    This keeps the same output shape as the previous DDG version so that
    existing researcher / caller code can continue to do json.loads(...)
    into a list of {title, url, snippet}.
    """
    try:
        client = _get_tavily_client()
    except Exception as e:  # noqa: BLE001
        # 没有配置 key 或初始化失败，返回一个带 error 的空结果
        payload: List[Dict[str, Any]] = [
            {
                "title": "",
                "url": "",
                "snippet": f"[web_search error] {e}",
            }
        ]
        return json.dumps(payload, ensure_ascii=False)

    try:
        # Tavily 官方客户端：返回 dict，包含 "results" 等字段
        resp = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",       # 保守一点，basic 即可
            include_answer=False,
            include_raw_content=False,
        )
    except Exception as e:  # noqa: BLE001
        payload: List[Dict[str, Any]] = [
            {
                "title": "",
                "url": "",
                "snippet": f"[web_search error calling Tavily] {e}",
            }
        ]
        return json.dumps(payload, ensure_ascii=False)

    results_out: List[Dict[str, Any]] = []
    for r in (resp.get("results") or []):
        results_out.append(
            {
                "title": r.get("title", "") or "",
                "url": r.get("url", "") or "",
                # Tavily 用的是 "content" 字段，这里映射到 snippet，兼容原接口
                "snippet": r.get("content", "") or "",
            }
        )

    return json.dumps(results_out, ensure_ascii=False)