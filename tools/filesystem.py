import os
from typing import List
from pydantic import BaseModel, Field
from langchain.tools import tool


class WriteFileArgs(BaseModel):
    path: str = Field(description="File path relative to workspace/, e.g. 'src/app.py' or 'index.html'")
    content: str = Field(description="Full file content to write")


@tool(args_schema=WriteFileArgs)
def write_file(path: str, content: str) -> str:
    """Write content to workspace/<path> and return the absolute path."""
    base = os.path.abspath("workspace")
    path = _normalize_path(path)
    abs_path = os.path.abspath(os.path.join(base, path))
    if not abs_path.startswith(base):
        raise ValueError("Refuse to write outside workspace/")

    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)
    return abs_path


class ReadFileArgs(BaseModel):
    path: str = Field(description="File path relative to workspace/")


@tool(args_schema=ReadFileArgs)
def read_file(path: str) -> str:
    """Read workspace/<path> and return content."""
    base = os.path.abspath("workspace")
    path = _normalize_path(path)
    abs_path = os.path.abspath(os.path.join(base, path))
    if not abs_path.startswith(base):
        raise ValueError("Refuse to read outside workspace/")

    with open(abs_path, "r", encoding="utf-8") as f:
        return f.read()


class ListDirArgs(BaseModel):
    path: str = Field(default="", description="Directory path relative to workspace/")


@tool(args_schema=ListDirArgs)
def list_dir(path: str = "") -> List[str]:
    """List files under workspace/<path>."""
    base = os.path.abspath("workspace")
    path = _normalize_path(path)
    abs_dir = os.path.abspath(os.path.join(base, path))
    if not abs_dir.startswith(base):
        raise ValueError("Refuse to list outside workspace/")

    if not os.path.exists(abs_dir):
        return []
    out = []
    for root, _, files in os.walk(abs_dir):
        for fn in files:
            full = os.path.join(root, fn)
            out.append(os.path.relpath(full, base))
    return sorted(out)

import os

def _normalize_path(path: str) -> str:
    p = path.replace("\\", "/").strip()
    # 去掉 ./ 前缀
    if p.startswith("./"):
        p = p[2:]
    # 去掉 workspace/ 前缀（避免 workspace/workspace）
    if p.startswith("workspace/"):
        p = p[len("workspace/"):]
    return p