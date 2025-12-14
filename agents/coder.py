# agents/coder.py
from typing import TypedDict, List, Dict, Any
import json, os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from tools.init import TOOLS_BY_NAME
from dotenv import load_dotenv
load_dotenv("properties.env")
MODEL = os.getenv("OPENAI_MODEL")


class State(TypedDict, total=False):
    task: str
    spec: dict
    task_queue: List[dict]
    done_tasks: List[dict]
    test_log: str
    tests_passed: bool
    review: str
    evidence_pack: Dict[str, Any]


def coder_node(state: State) -> State:
    model = ChatOpenAI(model=MODEL).bind_tools(
        [
            TOOLS_BY_NAME["write_file"],
            TOOLS_BY_NAME["read_file"],
            TOOLS_BY_NAME["list_dir"],
            # 如果你想让 coder 自己拉 arXiv，可以顺便加：
            TOOLS_BY_NAME["web_fetch"],
        ]
    )

    queue = state.get("task_queue") or []
    done = state.get("done_tasks", []) or []

    # ========= 模式 1：有 planner 输出的任务队列，就按老逻辑跑 =========
    if queue:
        current = queue[0]
        rest = queue[1:]

        spec_json = json.dumps(state.get("spec", {}), ensure_ascii=False, indent=2)
        task_json = json.dumps(current, ensure_ascii=False, indent=2)

        messages = [
            SystemMessage(content=(
                "You are a Code Generation Agent. "
                "Implement exactly the CURRENT TASK. "
                "Use tools to read existing files if needed and write/modify files via write_file. "
                "Do NOT rewrite the same file repeatedly in one run."
            )),
            HumanMessage(content=f"""
PROJECT SPEC (JSON):
{spec_json}

CURRENT TASK (JSON):
{task_json}

Hard constraints for write_file:
- Must include BOTH path and content.
- path is relative to workspace/ (do NOT prefix with 'workspace/').
""")
        ]

        evidence = state.get("evidence_pack")
        if evidence is not None:
            messages.append(SystemMessage(
                content="EVIDENCE_PACK:\n" + json.dumps(evidence, ensure_ascii=False)
            ))

        written = set()
        for _ in range(3):
            ai = model.invoke(messages)
            messages.append(ai)
            if not isinstance(ai, AIMessage) or not ai.tool_calls:
                break

            for tc in ai.tool_calls:
                name = tc["name"]
                args = tc.get("args", {}) or {}

                if name == "write_file":
                    if "path" not in args or "content" not in args:
                        messages.append(ToolMessage(
                            content=f"ERROR: write_file missing fields: {args}",
                            tool_call_id=tc["id"],
                        ))
                        continue
                    if args["path"] in written:
                        messages.append(ToolMessage(
                            content=f"SKIP: already wrote {args['path']} in this run",
                            tool_call_id=tc["id"],
                        ))
                        continue
                    written.add(args["path"])

                tool = TOOLS_BY_NAME.get(name)
                if not tool:
                    messages.append(ToolMessage(
                        content=f"ERROR: unknown tool {name}",
                        tool_call_id=tc["id"],
                    ))
                    continue

                try:
                    out = tool.invoke(args)
                    messages.append(ToolMessage(content=str(out), tool_call_id=tc["id"]))
                except Exception as e:
                    messages.append(ToolMessage(
                        content=f"ERROR: tool failed: {e}",
                        tool_call_id=tc["id"],
                    ))

        done.append(current)
        return {**state, "task_queue": rest, "done_tasks": done}

    # ========= 模式 2：没有 planner / task_queue，直接根据 task 一次性生成项目 =========

    user_task = (state.get("task") or "").strip()
    if not user_task:
        # 没有任何任务描述，就什么都不做
        return state

    # 这里直接把“自然语言任务”喂给 coder，让它把整个项目写出来
    messages = [
        SystemMessage(content=(
            "You are a Code Generation Agent. "
            "Given a project description, create ALL necessary project files in the workspace/ directory. "
            "This is a one-shot build: design a minimal but complete solution, then implement it. "
            "Use write_file to create/overwrite files; use read_file/list_dir only if you truly need context. "
            "Do NOT rewrite the same file multiple times in a single run."
        )),
        HumanMessage(content=f"""
PROJECT DESCRIPTION (natural language):
{user_task}

Requirements:
- Create a static website project for this task under the current directory (workspace/).
- Include HTML/CSS/JS files as needed to satisfy the description.
- Use only relative paths; when calling write_file:
  - 'path' MUST be relative to workspace/ (do NOT prefix with 'workspace/').
  - MUST include both 'path' and 'content'.
- Avoid placeholder/fake content if the task explicitly requires real data.
""")
    ]

    written = set()
    # 一次性生成项目，可以多给几轮工具调用
    for _ in range(8):
        ai = model.invoke(messages)
        messages.append(ai)
        if not isinstance(ai, AIMessage) or not ai.tool_calls:
            break

        for tc in ai.tool_calls:
            name = tc["name"]
            args = tc.get("args", {}) or {}

            if name == "write_file":
                if "path" not in args or "content" not in args:
                    messages.append(ToolMessage(
                        content=f"ERROR: write_file missing fields: {args}",
                        tool_call_id=tc["id"],
                    ))
                    continue
                if args["path"] in written:
                    messages.append(ToolMessage(
                        content=f"SKIP: already wrote {args['path']} in this run",
                        tool_call_id=tc["id"],
                    ))
                    continue
                written.add(args["path"])

            tool = TOOLS_BY_NAME.get(name)
            if not tool:
                messages.append(ToolMessage(
                    content=f"ERROR: unknown tool {name}",
                    tool_call_id=tc["id"],
                ))
                continue

            try:
                out = tool.invoke(args)
                messages.append(ToolMessage(content=str(out), tool_call_id=tc["id"]))
            except Exception as e:
                messages.append(ToolMessage(
                    content=f"ERROR: tool failed: {e}",
                    tool_call_id=tc["id"],
                ))

    # 单轮模式下，不维护 task_queue / done_tasks，原样返回 state 即可
    return state