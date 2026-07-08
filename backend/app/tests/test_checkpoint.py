"""Checkpoint + Rollback 测试"""

from langgraph.checkpoint.memory import MemorySaver

from app.core.checkpoint import get_checkpointer


def test_memory_saver_created():
    """MemorySaver 实例正确创建"""
    cp = get_checkpointer(store="memory")
    assert isinstance(cp, MemorySaver)


def test_checkpoint_used_in_graph():
    """Checkpoint 在主图编译中正确注入并可获取 state"""
    from app.modules.planner.graph import build_travel_planner_graph
    graph = build_travel_planner_graph()
    assert graph.checkpointer is not None
    # 通过 graph.get_state 测试 checkpoint 功能
    config = {"configurable": {"thread_id": "test-checkpoint"}}
    state = graph.get_state(config)
    assert state is not None
