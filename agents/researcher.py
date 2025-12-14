# agents/researcher.py
import json, os
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from tools.init import TOOLS_BY_NAME
from tools.web_search import web_search
from tools.web_fetch import web_fetch
from dotenv import load_dotenv
load_dotenv("properties.env")
MODEL = os.getenv("OPENAI_MODEL")

RESEARCH_SYSTEM = """You are a Research Agent.
You help other agents by collecting web evidence.

You MUST build an evidence_pack JSON object with the following keys:
- "queries": list of search queries you actually used.
- "sources": list of objects describing useful URLs or pages.
- "notes": list of short takeaways for the coding task.
- "gotchas": list of potential pitfalls / rate limits / quirks.
- "recommended_examples": list of example URLs or code snippets to follow.

When you return the final answer (no tool calls), ALWAYS return ONLY valid JSON for this evidence_pack."""

def researcher_node(state):
    return state
    task_text = state.get("task") or state.get("spec", {}).get("task", "")

    model = ChatOpenAI(model=MODEL, temperature=0).bind_tools(
        [TOOLS_BY_NAME["web_fetch"], TOOLS_BY_NAME["web_search"]]
    )

    msgs = [
        SystemMessage(content=RESEARCH_SYSTEM),
        HumanMessage(content=f"""
Task:
{task_text}

Steps:
1) Use web_search to find official docs and reliable references (3-5 queries).
2) Use web_fetch to fetch 2-4 best pages.
3) Produce evidence_pack JSON with sources + notes + gotchas + recommended_examples.
""")
    ]

    # 先准备一个 evidence，边跑工具边填充，确保不会是空的
    evidence = {
        "queries": [],
        "sources": [],
        "notes": [],
        "gotchas": [],
        "recommended_examples": [],
    }

    # 第一轮，让模型决定要不要用工具
    ai = model.invoke(msgs)

    if getattr(ai, "tool_calls", None):
        msgs.append(ai)
        for tc in ai.tool_calls:
            name = tc["name"]
            args = tc["args"] or {}

            try:
                if name == "web_search":
                    raw = web_search.invoke(args)
                    # 记录 query
                    q = args.get("query", "")
                    if q:
                        evidence["queries"].append(q)

                    # 解析结果列表
                    try:
                        results = json.loads(raw)
                    except Exception:
                        results = []

                    for item in results:
                        evidence["sources"].append({
                            "type": "search_result",
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("snippet", ""),
                        })

                elif name == "web_fetch":
                    raw = web_fetch.invoke(args)
                    try:
                        payload = json.loads(raw)
                    except Exception:
                        payload = {"raw": raw}

                    evidence["sources"].append({
                        "type": "fetched_page",
                        "url": payload.get("url", ""),
                        "status": payload.get("status", ""),
                        # 文本太长没必要全存，截个开头
                        "text": (payload.get("text") or "")[:1000],
                    })
                else:
                    # 未知工具
                    payload = {"tool": name, "error": "unknown tool", "args": args}
                    evidence["sources"].append(payload)

                # 把工具结果也作为 ToolMessage 回给模型
                tool_content = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
                msgs.append(ToolMessage(content=tool_content, tool_call_id=tc["id"]))

            except Exception as e:
                # 防御性兜底：工具崩溃也不要让 graph 崩
                err_payload = {"tool": name, "error": str(e), "args": args}
                evidence["sources"].append(err_payload)
                msgs.append(ToolMessage(content=json.dumps(err_payload, ensure_ascii=False),
                                        tool_call_id=tc["id"]))

        # 第二轮：让模型基于上面的 ToolMessages 来生成最终 evidence_pack JSON
        final = model.invoke(msgs)
        try:
            model_pack = json.loads(final.content)
            # 用模型总结出来的字段覆盖 / 合并
            for k in evidence.keys():
                if k in model_pack and isinstance(model_pack[k], list):
                    evidence[k] = model_pack[k]
        except Exception:
            # 如果模型输出不是合法 JSON，就把内容当成 note
            evidence["notes"].append(final.content)

    else:
        # 模型没有调用任何工具，直接尝试把 content 当 JSON
        try:
            evidence = json.loads(ai.content)
        except Exception:
            evidence["notes"].append(ai.content)

    state["evidence_pack"] = evidence
    return state