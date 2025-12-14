from typing import TypedDict, List
from tools.init import TOOLS_BY_NAME
from tools.shell import run_shell

class State(TypedDict, total=False):
    spec: dict
    task_queue: List[dict]
    done_tasks: List[dict]
    test_log: str
    tests_passed: bool

import json

def evaluator_node(state):
    spec = state["spec"]
    logs = []
    ok = True

    for cmd in spec["test_commands"]:
        raw = run_shell.invoke({"cmd": cmd, "timeout_s": 120})
        res = json.loads(raw)
        logs.append(res)
        if res["returncode"] != 0:
            ok = False
            break

    state["tests_passed"] = ok
    state["test_log"] = logs
    state["iter"] = state.get("iter", 0) + 1
    return state
