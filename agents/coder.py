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
            TOOLS_BY_NAME["web_fetch"],
        ]
    )


    user_task = (state.get("task") or "").strip()
    if not user_task:
        # 没有任何任务描述，就什么都不做
        return state
    # 可选：上一轮测试结果
    prev_tests = state.get("test_log")
    prev_passed = state.get("tests_passed")
    extra_test_info = ""
    if prev_tests is not None:
        # 测试信息压缩一下给 LLM 看
        extra_test_info = "\n\nPrevious test run:\n" + json.dumps(
            {
                "passed": prev_passed,
                "log": prev_tests,
            },
            ensure_ascii=False,
            indent=2,
        )

    spec = state.get("spec") or {}
    spec_json = json.dumps(spec, ensure_ascii=False, indent=2)
    evidence = state.get("evidence_pack") or {}
    evidence_json = json.dumps(evidence, ensure_ascii=False, indent=2)
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
{extra_test_info}
(If present) EVIDENCE_PACK from researcher:
{evidence_json}
(If present) SPEC (JSON, from analyzer):
{spec_json}

Requirements:
- Create a project for this task under the current directory (workspace/).
- Use only relative paths; when calling write_file:
  - 'path' MUST be relative to workspace/ (do NOT prefix with 'workspace/').
  - MUST include both 'path' and 'content'.
- Avoid placeholder/fake content if the task explicitly requires real data.
- If spec is available, strictly follow it.
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