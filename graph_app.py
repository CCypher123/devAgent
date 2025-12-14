# graph_app.py
from typing import TypedDict, List, Any, Dict
from langgraph.graph import StateGraph, START, END

from agents.coder import coder_node
from agents.reviewer import reviewer_node
from agents.evaluator import evaluator_node
from agents.analyzer import analyzer_node
from agents.researcher import researcher_node


class State(TypedDict, total=False):
    task: str
    # 以下字段都变成「可选」，coder/reviewer 用得到就用，用不到就算了
    spec: dict
    task_queue: List[dict]
    done_tasks: List[dict]
    test_log: str
    tests_passed: bool
    review: str
    test_targets: List[str]   # 例如 ["app.py", "scripts/check_data.py"]
    # evaluator 输出
    tests_passed: bool
    test_log: Any
    # 控制 evaluator→coder 的循环次数
    iter: int
    review: str
    # 可选：研究结果
    evidence_pack: Dict[str, Any]
    enable_research: bool  # 研究开关，默认 False

MAX_FIX_ITERS = 2  # 比如最多回 coder 修 2 轮

def route_after_evaluator(state: State) -> str:
    """
    - 如果 tests_passed 显式为 False 且迭代次数未超过上限 => 回 coder 尝试修复
    - 其他情况（True / 没有测试） => 直接去 reviewer
    """
    if state.get("tests_passed") is False and state.get("iter", 0) < MAX_FIX_ITERS:
        return "coder"
    return "reviewer"

def build_app():
    g = StateGraph(State)

    g.add_node("analyzer", analyzer_node)
    g.add_node("coder", coder_node)
    g.add_node("evaluator", evaluator_node)
    g.add_node("researcher", researcher_node)
    g.add_node("reviewer", reviewer_node)

    g.add_edge(START, "analyzer")
    g.add_edge("analyzer", "researcher")  # analyzer 之后进入 researcher
    g.add_edge("researcher", "coder")  # researcher 再进 coder
    g.add_edge("coder", "evaluator")

    g.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {
            "coder": "coder",
            "reviewer": "reviewer",
        },
    )

    g.add_edge("reviewer", END)
    return g.compile()