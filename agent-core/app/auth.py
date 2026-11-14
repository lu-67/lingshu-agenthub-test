"""图形验证码 + 注册/登录接口。"""
import base64, io, math, random, string, time
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from . import db, security

router = APIRouter(prefix="/api")


class RegisterReq(BaseModel):
    username: str = ""
    password: str = ""
    captchaId: str = ""
    captchaCode: str = ""


class LoginReq(BaseModel):
    username: str = ""
    password: str = ""


# 内存存验证码 {captcha_id: (code, expire_ts)} — 5 分钟有效
_CAPTCHA = {}
_CAPTCHA_TTL = 300


def _gc_captcha():
    now = time.time()
    dead = [k for k, v in _CAPTCHA.items() if v[1] < now]
    for k in dead:
        del _CAPTCHA[k]


@router.get("/captcha")
def get_captcha():
    """生成图形验证码，返回 {id, image(b64)}"""
    _gc_captcha()
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        # 没有 PIL 时用 4 位随机码 + 纯 JSON（前端 fallback）
        import uuid
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        cid = uuid.uuid4().hex
        _CAPTCHA[cid] = (code, time.time() + _CAPTCHA_TTL)
        return {"id": cid, "image": None, "code": code, "pilAvailable": False}

    # PIL 有 — 画 120×40 验证码
    w, h = 120, 40
    img = Image.new('RGB', (w, h), (248, 250, 252))
    d = ImageDraw.Draw(img)
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    for i, ch in enumerate(code):
        x = 14 + i * 26 + random.randint(-3, 3)
        y = 8 + random.randint(-2, 4)
        color = (random.randint(30, 90), random.randint(30, 90), random.randint(30, 90))
        angle = random.randint(-20, 20)
        try:
            font = ImageFont.truetype("arial.ttf", 26)
        except Exception:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 26)
            except Exception:
                font = ImageFont.load_default()
        # 用 text 画简单版（旋转用 draw.bitmap 太复杂）
        d.text((x, y), ch, fill=color, font=font)
    # 干扰线
    for _ in range(3):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = random.randint(0, w), random.randint(0, h)
        d.line([(x1, y1), (x2, y2)], fill=(random.randint(180, 220),)*3, width=1)
    # 干扰点
    for _ in range(30):
        d.point((random.randint(0, w), random.randint(0, h)), fill=(random.randint(200, 230),)*3)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode()
    import uuid
    cid = uuid.uuid4().hex
    _CAPTCHA[cid] = (code, time.time() + _CAPTCHA_TTL)
    return {"id": cid, "image": f"data:image/png;base64,{b64}", "pilAvailable": True}


def _check_captcha(cid: str, code: str) -> bool:
    if not cid or not code:
        return False
    entry = _CAPTCHA.get(cid)
    if not entry:
        return False
    expected, expire = entry
    if time.time() > expire:
        _CAPTCHA.pop(cid, None)
        return False
    _CAPTCHA.pop(cid, None)  # 一次性
    return expected.upper() == (code or '').upper()


def _issue_token(u: dict) -> dict:
    return {"token": security.make_token(u), "username": u["username"],
            "role": u["role"], "id": u["id"]}


@router.post("/auth/register")
def register(req: RegisterReq):
    username = (req.username or "").strip()
    password = req.password or ""
    # 验证码（生产环境必须，测试时设 SKIP_CAPTCHA=1 跳过）
    import os
    if not os.environ.get("SKIP_CAPTCHA") and not _check_captcha(req.captchaId, req.captchaCode):
        raise HTTPException(400, "验证码错误或已过期")
    # 用户名/密码校验
    if len(username) < 3 or len(username) > 20:
        raise HTTPException(400, "用户名长度需在 3–20 之间")
    if not __import__('re').match(r'^[a-zA-Z0-9_\-]+$', username):
        raise HTTPException(400, "用户名只能包含字母、数字、下划线、短横线")
    if len(password) < 6:
        raise HTTPException(400, "密码至少 6 个字符")
    if db.get_user_by_name(username):
        raise HTTPException(400, "用户名已存在")
    uid = db.create_user(username, security.hash_password(password))
    return _issue_token(db.get_user_by_id(uid))


@router.post("/auth/login")
def login(req: LoginReq):
    u = db.get_user_by_name((req.username or "").strip())
    if not u or not security.verify_password(req.password or "", u["password_hash"]):
        raise HTTPException(400, "密码错误或用户不存在")
    return _issue_token(u)


@router.get("/auth/me")
def me(user: dict = Depends(security.current_user)):
    uid = user["id"]
    try:
        stats = {
            "agents":   db.scalar(f"SELECT COUNT(*) FROM agents   WHERE owner_id={uid}") or 0,
            "sessions": db.scalar(f"SELECT COUNT(*) FROM sessions WHERE owner_id={uid}") or 0,
            "tasks":    db.scalar(f"SELECT COUNT(*) FROM tasks    WHERE owner_id={uid}") or 0,
        }
    except Exception:
        stats = {"agents": 0, "sessions": 0, "tasks": 0}
    ca = user.get("created_at")
    return {
        "id": uid,
        "username": user["username"],
        "role": user["role"],
        "createdAt": str(ca)[:19] if ca else None,
        "stats": stats,
    }
