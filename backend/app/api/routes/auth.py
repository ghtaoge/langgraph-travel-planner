"""认证 API 路由 — 注册、登录、获取当前用户"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas.auth import RegisterRequest, LoginRequest, LoginResponse, UserResponse
from app.core.auth import hash_password, verify_password, create_access_token, get_current_user
from app.core.database import get_db_pool, create_user, get_user_by_username

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest):
    """注册新用户 — 返回 JWT"""
    pool = await get_db_pool()

    # 检查用户名是否已存在
    existing = await get_user_by_username(pool, request.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建用户
    password_hash = hash_password(request.password)
    user = await create_user(pool, request.username, password_hash)

    # 生成 JWT
    token = create_access_token(user["id"], user["username"])

    return LoginResponse(
        access_token=token,
        user_id=user["id"],
        username=user["username"],
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """登录 — 返回 JWT"""
    pool = await get_db_pool()

    user = await get_user_by_username(pool, request.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(user["id"], user["username"])

    return LoginResponse(
        access_token=token,
        user_id=user["id"],
        username=user["username"],
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        created_at=current_user.get("created_at", ""),
    )
