from typing import TypedDict, List, Dict, Any
import json, os, re
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv("properties.env")
MODEL = os.getenv("OPENAI_MODEL")


class ProjectSpec(BaseModel):
    project_name: str
    description: str
    repo_type: str = Field(description="e.g. 'static_website', 'python_cli', 'python_web'")
    files: List[Dict[str, Any]] = Field(description="List of files to create with short purpose")
    build_instructions: List[str] = Field(default_factory=list)
    test_commands: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)


class State(TypedDict, total=False):
    task: str
    spec: dict
    task_queue: List[dict]
    done_tasks: List[dict]
    test_log: str
    tests_passed: bool
    review: str


PLANNER_SYSTEM = """You are a Project Planning Agent.
Return ONLY valid JSON (no markdown, no explanation)."""

def _extract_json(s: str) -> str:
    # 容错：模型偶尔会夹带文字，提取第一个大括号 JSON
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        raise ValueError("No JSON object found in model output")
    return m.group(0)


def planner_node(state: State) -> State:
    model = ChatOpenAI(model=MODEL)
    user_task = state["task"]

    prompt = f"""
User task:
{user_task}

Output JSON with exactly two top-level keys:
1) "spec": {{
   "project_name": "...",
   "description": "...",
   "repo_type": "static_website|python_cli|python_web",
   "files": [{{"path": "...", "purpose": "..."}}...],
   "build_instructions": [...],
   "test_commands": [...],
   "acceptance_criteria": [...]
}}
2) "tasks": [{{"id": "...", "goal": "...", "inputs": [...], "outputs": [...], "notes": "..."}}...]

Rules:
- All file paths MUST be relative to repo root (workspace/). Do NOT prefix with "workspace/".
- test_commands run with CWD=workspace/. Do NOT reference "workspace/" in commands.
- If the task involves any external data/API:
  - acceptance_criteria MUST include checks for "real data is non-empty" and "no placeholder/fake content".
  - spec.files MUST include a generator script and a validate.py.
  - test_commands MUST include: python <generator_script> and python validate.py
- Tasks must be STAGED (not one task per file). Avoid rewriting the same core file across multiple tasks.
  Suggested stages: scaffold -> generator -> templates/ui -> validate -> polish.
- "tasks" MUST be 3~8 high-level stages, NOT more.
- Each task should cover a coherent stage (e.g. scaffold structure, implement generator, implement templates, write validate, polish). Do NOT create one task per file.
"""

    resp = model.invoke([
        SystemMessage(content=PLANNER_SYSTEM),
        HumanMessage(content=prompt)
    ]).content

    data = json.loads(_extract_json(resp))
    spec = ProjectSpec(**data["spec"]).model_dump()
    tasks = data["tasks"]

    return {**state, "spec": spec, "task_queue": tasks, "done_tasks": []}