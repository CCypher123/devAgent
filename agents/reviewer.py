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

Give a concise review:
- Whether the acceptance criteria are met
- Structure and readability
- Clearly identify 2–4 areas for improvement
- If there are no test results (passed is null), conduct a subjective evaluation based solely on the file structure and the task description
"""
    return {"review": model.invoke(prompt).content}