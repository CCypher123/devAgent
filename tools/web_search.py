import json
from pydantic import BaseModel, Field
from langchain.tools import tool

class WebSearchArgs(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(default=5, ge=1, le=10)

@tool(args_schema=WebSearchArgs)
def web_search(query: str, max_results: int = 5) -> str:
    """Real web search via DuckDuckGo. Returns JSON list[{title,url,snippet}]."""
    from ddgs import DDGS
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })
    return json.dumps(results, ensure_ascii=False)