# tools/web_fetch.py
import json
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from pydantic import BaseModel, Field
from langchain.tools import tool


class WebFetchArgs(BaseModel):
    url: str = Field(description="URL to fetch (can be HTML page or API endpoint)")
    timeout_s: int = Field(default=20, ge=5, le=60, description="Per-request timeout in seconds")
    max_bytes: int = Field(
        default=50000,
        ge=1000,
        le=200000,
        description="Max response bytes to read (to avoid huge downloads)"
    )


@tool(args_schema=WebFetchArgs)
def web_fetch(url: str, timeout_s: int = 20, max_bytes: int = 50000) -> str:
    """
    Fetch a URL using Python standard library (urllib) and return JSON string.

    Response JSON schema:
    {
      "url": "<requested url>",
      "status": 200,            # or HTTP status code / null on network error
      "error": "<error msg>",   # empty string on success
      "text": "<response body decoded as text (truncated)>"
    }

    Notes:
    - No HTML parsing is done here; this is suitable for APIs (e.g. arXiv Atom XML).
    - Caller (LLM) is expected to inspect `.status` and `.text`.
    """
    headers = {
        # 伪装一个正常 UA，避免部分站点拒绝
        "User-Agent": "devAgent-web-fetch/1.0 (+https://example.local)"
    }

    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            status = getattr(resp, "status", 200)
            # 限制读取字节数，避免太大
            data = resp.read(max_bytes)
            # 尝试从 header 推断编码，默认 utf-8
            content_type = resp.headers.get("Content-Type", "")
            charset: Optional[str] = None
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()
            if not charset:
                charset = "utf-8"

            try:
                text = data.decode(charset, errors="replace")
            except LookupError:
                # 万一遇到怪编码，退回 utf-8
                text = data.decode("utf-8", errors="replace")

            payload = {
                "url": url,
                "status": status,
                "error": "",
                "text": text,
            }
            return json.dumps(payload, ensure_ascii=False)

    except HTTPError as e:
        payload = {
            "url": url,
            "status": e.code,
            "error": f"HTTPError: {e}",
            "text": "",
        }
        return json.dumps(payload, ensure_ascii=False)
    except URLError as e:
        payload = {
            "url": url,
            "status": None,
            "error": f"URLError: {e}",
            "text": "",
        }
        return json.dumps(payload, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        payload = {
            "url": url,
            "status": None,
            "error": f"Unexpected error: {e}",
            "text": "",
        }
        return json.dumps(payload, ensure_ascii=False)