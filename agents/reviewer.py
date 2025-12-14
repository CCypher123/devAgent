from typing import TypedDict, List
import json, os
from langchain_openai import ChatOpenAI
from tools.init import TOOLS_BY_NAME
from dotenv import load_dotenv
load_dotenv("properties.env")
MODEL = os.getenv("OPENAI_MODEL")

class State(TypedDict, total=False):
    task: str
    spec: dict
    done_tasks: List[dict]
    test_log: str
    tests_passed: bool
    review: str


def reviewer_node(state: State) -> State:
    model = ChatOpenAI(model=MODEL)
    files = TOOLS_BY_NAME["list_dir"].invoke({"path": ""})
    spec_json = json.dumps(state.get("spec", {}), ensure_ascii=False, indent=2)

    prompt = f"""
You are a Code Evaluation Agent.
Assess project quality against the spec.

SPEC:
{spec_json}

FILES IN workspace/:
{files}

TESTS:
passed={state.get("tests_passed")}
log:
{state.get("test_log","")}

Give a concise Chinese review:
- 是否满足 acceptance_criteria
- 结构与可读性
- 明确指出 2~4 个可改进点
- 如果没有测试结果（passed 为 null），就只根据文件结构和任务描述进行主观评估。
"""
    return {"review": model.invoke(prompt).content}