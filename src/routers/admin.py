"""
管理员鉴权路由
"""

import hashlib
import json
import os
import time
from typing import Dict
from fastapi import APIRouter, Request
from ..logger import logger
from ..schemas import AdminLoginRequest, AdminSetPasswordRequest

router = APIRouter(prefix="/api", tags=["admin"])

_admin_tokens: Dict[str, float] = {}
_ADMIN_TOKEN_TTL = 86400

_config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_admin_config_path = os.path.join(_config_dir, "admin_config.json")


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def _load_admin_password_hash() -> str:
    if os.path.exists(_admin_config_path):
        try:
            with open(_admin_config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("password_hash", "")
        except Exception:
            return ""
    return ""


def _save_admin_password_hash(password_hash: str):
    with open(_admin_config_path, 'w', encoding='utf-8') as f:
        json.dump({"password_hash": password_hash}, f)


def _is_admin_authenticated(request: Request) -> bool:
    token = request.headers.get("X-Admin-Token", "")
    if not token or token not in _admin_tokens:
        return False
    if time.time() - _admin_tokens[token] > _ADMIN_TOKEN_TTL:
        del _admin_tokens[token]
        return False
    return True


def _cleanup_expired_tokens():
    now = time.time()
    expired = [t for t, ts in _admin_tokens.items() if now - ts > _ADMIN_TOKEN_TTL]
    for t in expired:
        del _admin_tokens[t]


@router.post("/admin-login")
async def admin_login(req: AdminLoginRequest):
    stored_hash = _load_admin_password_hash()
    if not stored_hash:
        return {"success": False, "message": "管理员密码未设置，请先设置密码"}

    input_hash = _hash_password(req.password)
    if input_hash == stored_hash:
        import uuid
        token = str(uuid.uuid4())
        _cleanup_expired_tokens()
        _admin_tokens[token] = time.time()
        logger.info("管理员登录成功")
        return {"success": True, "token": token}

    logger.warning("管理员登录失败：密码错误")
    return {"success": False, "message": "密码错误"}


@router.post("/admin-set-password")
async def admin_set_password(req: AdminSetPasswordRequest):
    stored_hash = _load_admin_password_hash()
    if stored_hash:
        return {"success": False, "message": "密码已设置，请使用修改密码功能"}

    password_hash = _hash_password(req.password)
    _save_admin_password_hash(password_hash)
    logger.info("管理员密码设置成功")
    return {"success": True, "message": "密码设置成功"}


@router.get("/admin-status")
async def admin_status(request: Request):
    has_password = bool(_load_admin_password_hash())
    is_logged_in = _is_admin_authenticated(request)
    return {"has_password": has_password, "is_logged_in": is_logged_in}


@router.post("/admin-logout")
async def admin_logout(request: Request):
    token = request.headers.get("X-Admin-Token", "")
    if token in _admin_tokens:
        del _admin_tokens[token]
    return {"success": True}
