"""认证 API 数据模型"""

from pydantic import BaseModel, Field, field_validator
import re

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    """注册请求 — 登录账号只能是手机号或邮箱, 昵称仅用于展示"""
    account: str = Field(..., min_length=5, max_length=120, description="手机号或邮箱")
    password: str = Field(..., min_length=8, max_length=100, description="密码")
    nickname: str = Field(..., min_length=1, max_length=30, description="昵称")

    @field_validator("account")
    @classmethod
    def validate_account(cls, value: str) -> str:
        value = value.strip()
        if PHONE_RE.match(value) or EMAIL_RE.match(value):
            return value
        raise ValueError("账号只能使用手机号或邮箱")

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("昵称不能为空")
        return value


class LoginRequest(BaseModel):
    """登录请求"""
    account: str = Field(..., min_length=5, max_length=120, description="手机号或邮箱")
    password: str = Field(..., description="密码")

    @field_validator("account")
    @classmethod
    def validate_account(cls, value: str) -> str:
        value = value.strip()
        if PHONE_RE.match(value) or EMAIL_RE.match(value):
            return value
        raise ValueError("请输入手机号或邮箱")


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    nickname: str = ""
    phone: str = ""
    email: str = ""
    phone_verified: bool = False
    email_verified: bool = False
    avatar_url: str = ""
    theme: str = "dark"


class UserResponse(BaseModel):
    """用户信息响应"""
    id: str
    username: str
    nickname: str = ""
    phone: str = ""
    email: str = ""
    phone_verified: bool = False
    email_verified: bool = False
    avatar_url: str = ""
    theme: str = "dark"
    created_at: str = ""


class UpdateProfileRequest(BaseModel):
    """更新用户资料"""
    nickname: str | None = Field(default=None, min_length=1, max_length=30)
    avatar_url: str | None = Field(default=None, max_length=200000)
    theme: str | None = Field(default=None, pattern="^(dark|light|system)$")



class SendVerificationCodeRequest(BaseModel):
    """发送验证码"""
    target_type: str = Field(..., pattern="^(phone|email)$")
    target: str = Field(..., min_length=5, max_length=120)
    purpose: str = Field(..., pattern="^(reset_password|bind_account|change_password)$")


class BindAccountRequest(BaseModel):
    """绑定手机或邮箱"""
    target_type: str = Field(..., pattern="^(phone|email)$")
    target: str = Field(..., min_length=5, max_length=120)
    code: str = Field(..., min_length=4, max_length=12)


class ResetPasswordRequest(BaseModel):
    """忘记密码重置"""
    account: str = Field(..., min_length=5, max_length=120)
    code: str = Field(..., min_length=4, max_length=12)
    new_password: str = Field(..., min_length=8, max_length=100)


class ChangePasswordRequest(BaseModel):
    """修改密码 — 需要验证码"""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    target_type: str = Field(..., pattern="^(phone|email)$")
    code: str = Field(..., min_length=4, max_length=12)
