# agents/analyzer.py
from typing import TypedDict
import json, os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv("properties.env")
MODEL = os.getenv("OPENAI_MODEL")


class State(TypedDict, total=False):
    task: str
    spec: dict


def analyzer_node(state: State) -> State:
    model = ChatOpenAI(model=MODEL)

    task = state.get("task", "")
    if not task:
        return state

    system = (
        "You are a Task Analysis Agent.\n"
        "Given a natural language project description, you produce a MINIMAL JSON spec "
        "that summarizes the website structure and key requirements.\n"
        "Return ONLY valid JSON (no markdown)."
    )

    user = f"""
Task:
{task}

Output JSON with keys:
- project_name: short string
- pages: list of pages, each: {{"path": "...", "purpose": "..."}}
- assets: list of asset files (css/js) if needed
- notes: short free-form notes (array of strings)
"""

    resp = model.invoke([
        SystemMessage(content=system),
        HumanMessage(content=user),
    ])

    try:
        spec = json.loads(resp.content)
    except Exception:
        # 容错：解析失败就留空
        return state

    state["spec"] = spec
    return state