# agents/researcher.py
from typing import TypedDict, Dict, Any
import json, os

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from dotenv import load_dotenv

from tools.init import TOOLS_BY_NAME

load_dotenv("properties.env")
MODEL = os.getenv("OPENAI_MODEL")


class State(TypedDict, total=False):
    task: str
    spec: dict
    evidence_pack: Dict[str, Any]
    enable_research: bool


RESEARCH_SYSTEM = (
    "You are a Research Agent.\n"
    "Your job is to collect a small, focused evidence_pack for downstream coding.\n"
    "You MAY use the `web_search` tool to discover relevant URLs and the `web_fetch` tool "
    "to retrieve detailed content (API docs, examples, etc.).\n"
    "Always return a compact JSON object as your final answer.\n"
)


def researcher_node(state: State) -> State:
    """
    Research Agent（可选）：
    - 当 state.enable_research 为 True 时：执行简单的 search + fetch 流程，产出 evidence_pack。
    - 当未启用时：直接返回 state，不做任何事，不影响当前工作流稳定性。
    """

    # 1) 默认不开研究
    if not state.get("enable_research", False):
        if "evidence_pack" not in state:
            state["evidence_pack"] = {}
        return state

    task_text = (state.get("task") or "").strip()
    spec = state.get("spec") or {}

    model = ChatOpenAI(model=MODEL).bind_tools(
        [
            TOOLS_BY_NAME["web_search"],
            TOOLS_BY_NAME["web_fetch"],
        ]
    )

    # 2) 第一步：让 LLM 计划要查什么、调哪些工具
    messages = [
        SystemMessage(content=RESEARCH_SYSTEM),
        HumanMessage(content=f"""
Task description:
{task_text}

High-level spec (if any, JSON):
{json.dumps(spec, ensure_ascii=False, indent=2)}

Your goals:
- Optionally call web_search to find relevant URLs.
- Optionally call web_fetch on 1–3 highly relevant URLs (e.g., API manuals, reference docs).
- Finally, summarize everything into a JSON evidence_pack with keys:
  - "sources": brief list of {{title, url}} or similar
  - "notes": short bullet notes (list of strings)
  - "gotchas": edge cases / pitfalls (list of strings)
  - "recommended_examples": short code / URL pointers (list of strings)
If tools are not available or fail, still return a best-effort JSON based on your own knowledge.
""")
    ]

    # 工具调用最多十轮，避免过度搜索
    for _ in range(10):
        ai = model.invoke(messages)
        messages.append(ai)

        if not isinstance(ai, AIMessage) or not getattr(ai, "tool_calls", None):
            # 没有工具调用，直接把 ai.content 当成最终 JSON 尝试解析
            try:
                evidence = json.loads(ai.content)
            except Exception:
                evidence = {"notes": [ai.content]}
            state["evidence_pack"] = evidence
            return state

        # 有 tool_calls：执行工具，再让模型总结一次
        for tc in ai.tool_calls:
            name = tc["name"]
            args = tc.get("args") or {}
            tool = TOOLS_BY_NAME.get(name)
            if not tool:
                messages.append(ToolMessage(
                    content=f"ERROR: unknown tool {name}",
                    tool_call_id=tc["id"],
                ))
                continue

            try:
                out = tool.invoke(args)
                messages.append(ToolMessage(
                    content=str(out),
                    tool_call_id=tc["id"],
                ))
            except Exception as e:  # noqa: BLE001
                messages.append(ToolMessage(
                    content=f"ERROR: tool failed: {e}",
                    tool_call_id=tc["id"],
                ))

        # 再让模型汇总一次，产出 evidence_pack JSON
        final = model.invoke(messages)
        try:
            evidence = json.loads(final.content)
        except Exception:
            evidence = {"notes": [final.content]}
        state["evidence_pack"] = evidence
        return state

    # 理论上不会跑到这里，兜底一下
    if "evidence_pack" not in state:
        state["evidence_pack"] = {}
    return state