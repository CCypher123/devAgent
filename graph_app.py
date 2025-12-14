# graph_app.py
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END

from agents.coder import coder_node
from agents.reviewer import reviewer_node


class State(TypedDict, total=False):
    task: str
    # 以下字段都变成「可选」，coder/reviewer 用得到就用，用不到就算了
    spec: dict
    task_queue: List[dict]
    done_tasks: List[dict]
    test_log: str
    tests_passed: bool
    review: str


def build_app():
    g = StateGraph(State)

    g.add_node("coder", coder_node)
    g.add_node("reviewer", reviewer_node)

    g.add_edge(START, "coder")
    g.add_edge("coder", "reviewer")
    g.add_edge("reviewer", END)

    return g.compile()