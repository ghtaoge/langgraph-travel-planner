"""认证 API 路由 — 注册、登录、用户设置、验证码、找回密码"""

import random
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas.auth import (
    BindAccountRequest,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    ResetPasswordRequest,
    SendVerificationCodeRequest,
    UpdateProfileRequest,
    UserResponse,
)
from app.config.settings import settings
from app.core.auth import create_access_token, get_current_user, get_optional_current_user, hash_password, verify_password
from app.core.database import (
    bind_user_account,
    consume_verification_code,
    create_account_user,
    create_verification_code,
    get_db_pool,
    get_user_by_account,
    update_user_password,
    update_user_profile,
)

router = APIRouter(prefix="/api/auth", tags=["认证"])

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_target(target_type: str, target: str) -> str:
    value = target.strip()
    if target_type == "phone" and PHONE_RE.match(value):
        return value
    if target_type == "email" and EMAIL_RE.match(value):
        return value.lower()
    raise HTTPException(status_code=422, detail="手机号或邮箱格式不正确")


def split_account(account: str) -> tuple[str, str]:
    value = account.strip()
    if PHONE_RE.match(value):
        return "phone", value
    if EMAIL_RE.match(value):
        return "email", value.lower()
    raise HTTPException(status_code=422, detail="账号只能使用手机号或邮箱")


def assert_reset_channel(target_type: str):
    channel = settings.PASSWORD_RESET_CHANNEL.lower()
    if channel not in {"phone", "email", "both"}:
        raise HTTPException(status_code=500, detail="密码找回通道配置错误")
    if channel != "both" and channel != target_type:
        label = "手机号" if channel == "phone" else "邮箱"
        raise HTTPException(status_code=400, detail=f"当前系统仅支持通过{label}找回密码")


def login_response(user: dict, token: str) -> LoginResponse:
    return LoginResponse(
        access_token=token,
        user_id=user["id"],
        username=user["username"],
        nickname=user.get("nickname", user["username"]),
        phone=user.get("phone", ""),
        email=user.get("email", ""),
        phone_verified=user.get("phone_verified", False),
        email_verified=user.get("email_verified", False),
        avatar_url=user.get("avatar_url", ""),
        theme=user.get("theme", "dark"),
    )


def make_code() -> str:
    return f"{random.randint(0, 999999):06d}"


async def issue_code(
    target_type: str,
    target: str,
    purpose: str,
    user_id: str | None = None,
    require_existing_user: bool = False,
):
    pool = await get_db_pool()
    normalized = normalize_target(target_type, target)
    user = await get_user_by_account(pool, normalized)
    if require_existing_user and not user:
        raise HTTPException(status_code=404, detail="账号不存在")

    code = make_code()
    expires_at = datetime.now() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)
    await create_verification_code(
        pool,
        target_type=target_type,
        target=normalized,
        purpose=purpose,
        code=code,
        expires_at=expires_at,
        user_id=user_id,
    )
    result = {"ok": True, "expires_in_minutes": settings.VERIFICATION_CODE_EXPIRE_MINUTES}
    if settings.DEV_RETURN_VERIFICATION_CODE:
        result["dev_code"] = code
    return result


@router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest):
    pool = await get_db_pool()
    target_type, account = split_account(request.account)
    existing = await get_user_by_account(pool, account)
    if existing:
        raise HTTPException(status_code=400, detail="账号已存在")

    phone = account if target_type == "phone" else None
    email = account if target_type == "email" else None
    user = await create_account_user(
        pool,
        username=account,
        password_hash=hash_password(request.password),
        nickname=request.nickname.strip(),
        phone=phone,
        email=email,
    )
    token = create_access_token(user["id"], user["username"])
    return login_response(user, token)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    pool = await get_db_pool()
    _, account = split_account(request.account)
    user = await get_user_by_account(pool, account)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="账号或密码错误")

    token = create_access_token(user["id"], user["username"])
    return login_response(user, token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(request: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    pool = await get_db_pool()
    user = await update_user_profile(
        pool,
        current_user["id"],
        nickname=request.nickname.strip() if request.nickname is not None else None,
        avatar_url=request.avatar_url.strip() if request.avatar_url is not None else None,
        theme=request.theme,
    )
    return UserResponse(**user)


@router.post("/verification-code")
async def send_verification_code(request: SendVerificationCodeRequest, current_user: dict | None = Depends(get_optional_current_user)):
    purpose = request.purpose
    target = normalize_target(request.target_type, request.target)

    if purpose == "reset_password":
        assert_reset_channel(request.target_type)
        return await issue_code(request.target_type, target, purpose, require_existing_user=True)

    if purpose == "bind_account":
        if current_user is None:
            raise HTTPException(status_code=401, detail="请先登录")
        pool = await get_db_pool()
        existing = await get_user_by_account(pool, target)
        if existing and existing["id"] != current_user["id"]:
            raise HTTPException(status_code=400, detail="该账号已被其他用户绑定")
        return await issue_code(request.target_type, target, purpose, user_id=current_user["id"])

    if purpose == "change_password":
        if current_user is None:
            raise HTTPException(status_code=401, detail="请先登录")
        bound_target = current_user.get(request.target_type)
        verified = current_user.get(f"{request.target_type}_verified")
        if not bound_target or bound_target != target or not verified:
            raise HTTPException(status_code=400, detail="请使用已验证绑定的手机号或邮箱")
        return await issue_code(request.target_type, target, purpose, user_id=current_user["id"])

    raise HTTPException(status_code=422, detail="验证码用途不支持")


@router.post("/bind-account", response_model=UserResponse)
async def bind_account(request: BindAccountRequest, current_user: dict = Depends(get_current_user)):
    pool = await get_db_pool()
    target = normalize_target(request.target_type, request.target)
    ok = await consume_verification_code(pool, request.target_type, target, "bind_account", request.code, current_user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    existing = await get_user_by_account(pool, target)
    if existing and existing["id"] != current_user["id"]:
        raise HTTPException(status_code=400, detail="该账号已被其他用户绑定")

    user = await bind_user_account(pool, current_user["id"], request.target_type, target)
    return UserResponse(**user)


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    pool = await get_db_pool()
    target_type, account = split_account(request.account)
    assert_reset_channel(target_type)
    user = await get_user_by_account(pool, account)
    if not user:
        raise HTTPException(status_code=404, detail="账号不存在")

    if not user.get(f"{target_type}_verified"):
        raise HTTPException(status_code=400, detail="该账号尚未完成验证, 无法找回密码")

    ok = await consume_verification_code(pool, target_type, account, "reset_password", request.code)
    if not ok:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    await update_user_password(pool, user["id"], hash_password(request.new_password))
    return {"ok": True}


@router.post("/change-password")
async def change_password(request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    pool = await get_db_pool()
    bound_target = current_user.get(request.target_type)
    verified = current_user.get(f"{request.target_type}_verified")
    if not bound_target or not verified:
        raise HTTPException(status_code=400, detail="请先绑定并验证该方式")

    user = await get_user_by_account(pool, bound_target)
    if not user or not verify_password(request.old_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="原密码不正确")

    ok = await consume_verification_code(pool, request.target_type, bound_target, "change_password", request.code, current_user["id"])
    if not ok:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    await update_user_password(pool, current_user["id"], hash_password(request.new_password))
    return {"ok": True}
