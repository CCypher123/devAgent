# agents/evaluator.py
from typing import TypedDict, List, Any
import json
from tools.init import TOOLS_BY_NAME


class State(TypedDict, total=False):
    test_targets: List[str]
    tests_passed: bool
    test_log: Any
    iter: int


def evaluator_node(state: State) -> State:
    """
    通用评测节点：
    - 仅在 state.test_targets 中有 .py 目标时，使用 run_shell 运行这些文件；
    - 对于“纯前端任务”，不设置 test_targets => evaluator 只记录“无测试”，不实际执行任何东西。
    """
    targets = state.get("test_targets") or []
    logs: List[Any] = []

    # 1) 没有任何测试目标：直接跳过
    if not targets:
        state["tests_passed"] = True   # 对这次任务来说视为通过
        state["test_log"] = "no tests requested"
        state["iter"] = state.get("iter", 0) + 1
        return state

    # 2) 有测试目标：执行 .py 文件
    run_shell = TOOLS_BY_NAME["run_shell"]

    ok = True
    for path in targets:
        # 只允许 .py 文件
        if not path.endswith(".py"):
            logs.append(
                {
                    "target": path,
                    "skipped": True,
                    "reason": "only .py files are allowed in evaluator",
                }
            )
            continue

        cmd = f"python {path}"
        raw = run_shell.invoke({"cmd": cmd, "timeout_s": 120})

        # 你的 run_shell 是返回 JSON 字符串，这里解析一下
        try:
            res = json.loads(raw)
        except Exception:
            res = {"raw": raw, "parse_error": True}

        res["target"] = path
        logs.append(res)

        if res.get("returncode", 1) != 0:
            ok = False

    state["tests_passed"] = ok
    state["test_log"] = logs
    state["iter"] = state.get("iter", 0) + 1
    return state