"""认证模块测试 — JWT + bcrypt"""

import pytest
from app.core.auth import hash_password, verify_password, create_access_token, decode_access_token
from app.config.settings import settings


def test_password_hash_and_verify():
    """bcrypt 哈希和校验"""
    password = "test_password_123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_create_and_decode():
    """JWT 生成和解码"""
    token = create_access_token("user-123", "testuser")
    payload = decode_access_token(token)
    assert payload["user_id"] == "user-123"
    assert payload["username"] == "testuser"


def test_jwt_invalid_token():
    """无效 JWT 解码应抛异常"""
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        decode_access_token("invalid.token.string")
