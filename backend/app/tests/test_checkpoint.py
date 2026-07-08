"""Checkpoint 测试 — AsyncPostgresSaver 初始化"""

import pytest


def test_checkpoint_module_imports():
    """验证 checkpoint 模块可导入"""
    from app.core.checkpoint import get_checkpointer, init_checkpointer, close_checkpointer
    assert get_checkpointer is not None
    assert init_checkpointer is not None


def test_store_module_imports():
    """验证 store 模块可导入"""
    from app.core.store import get_store, init_store, close_store
    assert get_store is not None
    assert init_store is not None
