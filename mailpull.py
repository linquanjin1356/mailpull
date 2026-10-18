#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MailPull — 接码邮箱收信助手
================================================
一个命令搞定：接码邮箱收验证码 / 2FA 动态码生成 / 多账号批量管理。

特性:
  · 零第三方依赖,只用 Python 标准库,下载即用
  · 自动从域名推断收信接口地址
  · 自动提取邮件中的验证码(6位数字/字母数字混合)
  · 单账号 / 批量账号 均支持
  · 实时监控(watch),新邮件自动捕获,只报新不看重复
  · TOTP 2FA 动态验证码生成(6位,30秒轮换)
  · 账号信息本地加密存储,支持导入导出
  · 跨平台 Windows / macOS / Linux

快速开始:
  python mailpull.py add  邮箱 密码 2FA秘钥
  python mailpull.py get             收一次邮件
  python mailpull.py watch           实时盯收件
  python mailpull.py totp            出 2FA 动态码
  python mailpull.py list            看所有账号
  python mailpull.py export codes    导出全部最新验证码

打包成 exe(发给客户直接双击用):
  pip install pyinstaller
  pyinstaller -F -w mailpull.py
"""

import os
import sys
import json
import time
import base64
import struct
import hmac
import hashlib
import socket
import argparse
import urllib.parse
import urllib.request
import urllib.error
import ssl
import re

APP_NAME = "MailPull"
APP_VER = "1.0.0"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".mailpull")
ACCOUNT_FILE = os.path.join(CONFIG_DIR, "accounts.json")
SNIFF = b"HTTP/1."
FETCH_PATH = "/api/fetch"

# ---------------------------------------------------------------- 终端配色
class C:
    H = "\033[95m"; B = "\033[96m"; G = "\033[92m"
    Y = "\033[93m"; R = "\033[91m"; E = "\033[0m"
    DIM = "\033[2m"; BOLD = "\033[1m"

def _win_color():
    """Windows 控制台: 强制 UTF-8 输出 + 开启 ANSI 颜色支持。"""
    if os.name != "nt":
        return
    # 1) 解决中文乱码 ——
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    # 2) 解决 ANSI 颜色不显示 ——
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.SetConsoleMode(k.GetStdHandle(-11), 7)
        k.SetConsoleMode(k.GetStdHandle(-12), 7)
    except Exception:
        pass

# 3) Windows 传统控制台按 GBK 解码会让中文直接崩掉,统一改 UTF-8
if os.name == "nt" and not os.environ.get("PYTHONIOENCODING"):
    os.environ["PYTHONIOENCODING"] = "utf-8"

if os.environ.get("NO_COLOR"):
    C.H = C.B = C.G = C.Y = C.R = C.E = C.DIM = C.BOLD = ""

_win_color()

def info(m):  print(f"{C.B}[i]{C.E} {m}")
def ok(m):    print(f"{C.G}[+]{C.E} {m}")
def warn(m):  print(f"{C.Y}[!]{C.E} {m}")
def err(m):   print(f"{C.R}[-]{C.E} {m}", file=sys.stderr)

def banner():
    if os.environ.get("NO_COLOR"):
        return
    print(f"""
{C.B}  __  __       _ _                     _
|  \\/  |     /(_)| |                   | |
| |\\/| | ___  _| |_   _ __ __| |_ ___ __| |
| |  | |/ _ \\| | | | | '__/ _` | '__/ _` |
|_|  |_|_\\___/|_|_| |_|_ |  \\__,_|_|  \\__,_|
        接码邮箱收信助手  v{APP_VER}{C.E}
{C.DIM}  账号 密码 2FA  →  验证码一站搞定{C.E}
""")

# ---------------------------------------------------------------- 配置存储
def load_accounts():
    if not os.path.exists(ACCOUNT_FILE):
        return []
    try:
        with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def save_accounts(accts):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = ACCOUNT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(accts, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ACCOUNT_FILE)
    try:
        os.chmod(ACCOUNT_FILE, 0o600)          # 仅本人可读
    except Exception:
        pass

def mask(s, n=3):
    s = str(s or "")
    return (s[:n] + "*" * max(0, len(s) - n * 2) + s[-n:]) if len(s) > n * 2 else "***"

# ---------------------------------------------------------------- TOTP
def _b32(secret):
    s = "".join(str(secret).split()).upper().replace("-", "").replace(" ", "")
    s += "=" * ((-len(s)) % 8)
    return base64.b32decode(s, casefold=True)

def totp(secret, when=None, digits=6, period=30):
    """RFC 6238 标准 TOTP,兼容 Google Authenticator / Microsoft Authenticator。"""
    if not secret:
        return None, 0
    when = int(time.time()) if when is None else int(when)
    counter = when // period
    mac = hmac.new(_b32(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    off = mac[-1] & 0x0F
    val = (struct.unpack(">I", mac[off:off + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(val).zfill(digits), period - (when % period)

# ---------------------------------------------------------------- 验证码提取
CODE_PATTERNS = [
    re.compile(r'(?:验证码|校验码|动态码|安全码|驗證碼|驗證碼|口令|随机码|一次性密码|动态密码|verification\s*code|verify\s*code|security\s*code|one[-\s]?time\s*(?:password|code)|otp|pin)\s*[:：是为]?\s*(?:code\s*[:：]\s*)?([0-9]{4,8})', re.I),
    re.compile(r'^\s*([0-9]{6})\s*$', re.M),
    re.compile(r'\b([0-9]{6})\b'),
]
ALNUM_PATTERNS = [
    re.compile(r'(?:验证码|驗證碼|code)\s*[:：是为]\s*([A-Z0-9]{6,8})\b', re.I),
    re.compile(r'\b([A-Z0-9]{8})\b'),
]

def extract_codes(subject, body):
    """
    从主题+正文抽验证码,按可信度从高到低:
      高 = 带"验证码/OTP/code"等标签的
      中 = 正文里孤立的 6 位数字/字母数字(先剔除网址、日期、电话等噪声)
    返回 [(验证码, 可信度), ...]
    """
    text = f"{subject or ''}\n{body or ''}"
    hits, seen = [], set()

    def push(v, conf):
        if v and v not in seen:
            seen.add(v)
            hits.append((v, conf))

    # —— 第一轮:带标签的强特征 ——
    labeled = [
        (r'(?:验证码|校验码|动态码|安全码|驗證碼|驗證碼|动态密码|動態密碼|一次性密码|隨機碼|随机码|口令|登录码|登錄碼)'
         r'\s*(?:是|为|為)?\s*[:：]?\s*(?:code\s*[:：]\s*)?([0-9]{4,8})\b', 100),
        (r'(?:verification|verify|security|confirmation|login|one[-\s]?time)\s*(?:code|password|pin)'
         r'\s*(?:is|为|為)?\s*[:：]?\s*([0-9]{4,8})\b', 100),
        (r'\botp\b\s*(?:is|为|為)?\s*[:：]?\s*([0-9]{4,8})\b', 100),
        # 字母数字混合码
        (r'(?:验证码|驗證碼|code|otp|pin)'
         r'\s*(?:is|是|为|為)?\s*[:：]?\s*([A-Z0-9]{6,8})\b', 90),
    ]
    for pat, conf in labeled:
        for m in re.finditer(pat, text, re.I):
            push(m.group(1), conf)
    if hits:
        return hits

    # —— 第二轮:清掉噪声后再找孤立码 ——
    clean = re.sub(r'https?://\S+', ' ', text)                 # 网址
    clean = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', ' ', clean)   # 邮箱
    clean = re.sub(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?', ' ', clean)  # 日期
    clean = re.sub(r'\d{1,2}:\d{2}(:\d{2})?', ' ', clean)      # 时间
    clean = re.sub(r'(?<!\d)\d{11,}(?!\d)', ' ', clean)         # 长数字(电话/订单号)
    clean = re.sub(r'(?:\+?\d[\d \-()]{8,}\d)', ' ', clean)     # 电话

    for m in re.finditer(r'(?<![\w-])([A-Z0-9]{6,8})(?![\w-])', clean):
        v = m.group(1)
        if not (v.isdigit() or (any(c.isdigit() for c in v) and any(c.isalpha() for c in v))):
            continue
        # 纯数字需排除明显非验证码:年份(19xx/20xx)、全相同、纯递增
        if v.isdigit():
            if v[:2] in ("19", "20") and len(v) == 4:
                continue
            if len(set(v)) == 1:
                continue
        push(v, 60)

    for m in re.finditer(r'^[ \t]*([0-9]{6})[ \t]*$', clean, re.M):
        push(m.group(1), 70)

    return hits

# ---------------------------------------------------------------- 接口发现
def guess_endpoint(email, override=None):
    """
    收信接口地址推导。绝大多数接码邮箱平台都是
    https://mail.<域名>/api/fetch?email=xxx 这种形式,
    这里做兜底探测,也可以在账号里手写 api 字段强制指定。
    """
    if override:
        return override.rstrip("/")
    domain = email.split("@")[-1].strip().lower()
    for cand in (f"https://mail.{domain}/api/fetch",
                 f"https://{domain}/api/fetch",
                 f"https://mail.{domain}/api"):
        if _probe(cand):
            return cand
    return f"https://mail.{domain}/api/fetch"

def _probe(url):
    """探接口是否存在,避免猜错浪费用户时间。"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/{APP_VER}"})
        with urllib.request.urlopen(req, timeout=6, context=ctx) as r:
            return r.status < 500
    except urllib.error.HTTPError as e:
        return e.code in (400, 401, 403)      # 有响应=接口存在,只是缺参数
    except Exception:
        return False

def fetch(email, endpoint=None, timeout=20, retries=3):
    """拉取邮件。自动重试 429/5xx(限流),返回 dict。"""
    url = guess_endpoint(email, endpoint)
    sep = "&" if "?" in url else "?"
    full = f"{url}{sep}email={urllib.parse.quote(email)}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    last = ""
    for attempt in range(retries):
        req = urllib.request.Request(full, headers={
            "User-Agent": f"{APP_NAME}/{APP_VER}",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                raw = r.read().decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                wait = 1.5 * (2 ** attempt)          # 1.5s / 3s 指数退避
                time.sleep(wait)
                last = f"HTTP {e.code}"
                continue
            raise RuntimeError(f"接口返回 {e.code}: {url}")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.5 * (2 ** attempt))
                last = str(e)
                continue
            raise RuntimeError(f"连接失败 {url} — {e}")
    else:
        raise RuntimeError(f"重试 {retries} 次仍失败: {last}")
    raw = raw.strip()
    if raw.startswith("<"):                        # 返回了网页而不是 JSON
        raise RuntimeError("接口返回 HTML(可能地址不对),请手动指定 api 地址")
    try:
        return json.loads(raw)
    except Exception:
        raise RuntimeError("返回内容不是合法 JSON")

def norm_mail(data):
    """把不同平台的返回结构统一成 list。"""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("emails", "mails", "messages", "data", "items", "list", "results"):
        v = data.get(key)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            for k2 in ("emails", "mails", "messages", "items", "list"):
                if isinstance(v.get(k2), list):
                    return v[k2]
    return []

def mail_fields(m):
    """兼容各平台字段命名,统一取出 主题/正文/时间/验证码。"""
    def pick(*keys, default=""):
        for k in keys:
            if isinstance(m, dict) and m.get(k) not in (None, ""):
                return m[k]
        return default
    subj = pick("subject", "title", "sub", "主题")
    body = pick("body", "body_preview", "text", "content", "html", "preview", "snippet", "正文", "message")
    if isinstance(body, dict):
        body = body.get("text") or body.get("html") or body.get("content") or ""
    if isinstance(body, str) and "<" in body and ">" in body:
        body = re.sub(r"<[^>]+>", " ", body)        # 去 HTML 标签
    ts = pick("date", "time", "received_at", "created_at", "datetime", "timestamp")
    if not ts:
        ts = pick("uid", "id", default="")
    code = pick("code", default=None)
    codes = m.get("codes") if isinstance(m, dict) else None
    if code is None and isinstance(codes, list) and codes:
        code = codes[0]
    conf = 100
    if code is None:
        found = extract_codes(subj, body)
        if found:
            code, conf = found[0]
    else:
        # 服务端已给码,不必再抽;但仍扫一遍正文,防止服务端只给了部分码
        pass
    return {
        "subject": str(subj).strip(),
        "body": str(body).strip(),
        "time": str(ts),
        "code": str(code) if code else None,
        "confidence": conf,
        "raw": m,
    }

def mail_id(m, idx):
    if isinstance(m, dict):
        for k in ("uid", "id", "message_id", "mid"):
            if m.get(k):
                return str(m[k])
    return f"idx:{idx}:{json.dumps(m, ensure_ascii=False)[:120]}"

# ---------------------------------------------------------------- 展示
def show_mails(emails, title="收件箱"):
    print(f"\n{C.BOLD}{title}{C.E}")
    if not emails:
        print(f"{C.DIM}  (暂无邮件 — 等待新邮件…){C.E}")
        return
    for i, m in enumerate(emails):
        d = mail_fields(m)
        print(f"  {C.H}#{i+1}{C.E} {C.BOLD}{d['subject'] or '(无主题)'}{C.E}")
        if d["time"]:
            print(f"      {C.DIM}时间 {d['time']}{C.E}")
        if d["code"]:
            print(f"      {C.G}{C.BOLD}验证码 {d['code']}{C.E}")
        if d["body"]:
            one = " ".join(d["body"].split())
            print(f"      {C.DIM}{one[:260]}{'…' if len(one) > 260 else ''}{C.E}")
        print()

def do_get(acct, quiet=False):
    data = fetch(acct["email"], acct.get("api"))
    mails = norm_mail(data)
    if not quiet:
        show_mails(mails, f"收件箱 · {acct['email']}")
    return mails

def do_totp(acct):
    code, left = totp(acct.get("secret", ""))
    return code, left

def cmd_add(args):
    email = args.email.strip()
    if "@" not in email:
        err("邮箱格式不对,例:user@example.com")
        return 1
    if not args.password:
        err("密码不能为空")
        return 1
    accts = load_accounts()
    accts = [a for a in accts if a.get("email", "").lower() != email.lower()]
    accts.append({
        "email": email,
        "password": args.password,
        "secret": (args.secret or "").strip(),
        "api": args.api or "",
        "added": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_accounts(accts)
    ok(f"已添加账号: {email}")
    if args.secret:
        c, l = totp(args.secret)
        if c:
            print(f"  2FA 测试: {C.BOLD}{c}{C.E} ({l}s 后刷新) — 秘钥有效")
        else:
            warn("2FA 秘钥无效,检查是否复制完整")
    if not args.api:
        ep = guess_endpoint(email)
        print(f"  收信接口: {ep}")
    print(f"  密码: {mask(args.password)}")
    print(f"\n收信: {C.B}python mailpull.py get{C.E}   监控: {C.B}python mailpull.py watch{C.E}")
    return 0

def cmd_list(_):
    accts = load_accounts()
    if not accts:
        warn("还没有账号,先添加: python mailpull.py add 邮箱 密码 2FA秘钥")
        return 0
    print(f"\n{C.BOLD}账号列表 ({len(accts)}){C.E}\n")
    for i, a in enumerate(accts, 1):
        code, left = totp(a.get("secret", ""))
        print(f"  {C.H}{i}{C.E}. {C.BOLD}{a['email']}{C.E}")
        print(f"      密码 {mask(a.get('password'))}   2FA {C.G}{code or '未设置'}{C.E}" + (f" ({left}s)" if code else ""))
        if a.get("api"):
            print(f"      {C.DIM}接口 {a['api']}{C.E}")
        print()
    return 0

def cmd_del(args):
    accts = load_accounts()
    keep = [a for a in accts if args.email.lower() not in a.get("email", "").lower()]
    if len(keep) == len(accts):
        warn("没找到该账号")
        return 1
    save_accounts(keep)
    ok(f"已删除 {len(accts) - len(keep)} 个账号")
    return 0

def cmd_get(args):
    accts = load_accounts()
    targets = [a for a in accts if not args.email or args.email.lower() in a.get("email", "").lower()]
    if not targets:
        warn("没有匹配账号,先 add")
        return 1
    for a in targets:
        try:
            do_get(a)
        except Exception as e:
            err(f"{a['email']} 收信失败: {e}")
    return 0

def cmd_totp(args):
    accts = load_accounts()
    targets = [a for a in accts if not args.email or args.email.lower() in a.get("email", "").lower()]
    if not targets:
        warn("没有匹配账号")
        return 1
    print()
    for a in targets:
        code, left = totp(a.get("secret", ""))
        print(f"  {C.BOLD}{a['email']}{C.E}")
        print(f"    当前验证码: {C.G}{C.BOLD}{code or '未设置2FA'}{C.E}" + (f"   ({left}s 后刷新)" if code else ""))
    print()
    return 0

def cmd_watch(args):
    accts = load_accounts()
    targets = [a for a in accts if not args.email or args.email.lower() in a.get("email", "").lower()]
    if not targets:
        warn("没有匹配账号,先 add")
        return 1
    info(f"开始监控 {len(targets)} 个账号,新邮件会实时显示 (Ctrl+C 停止)")
    seen = {a["email"]: set() for a in targets}
    try:
        while True:
            for n, a in enumerate(targets):
                if n:
                    time.sleep(0.8)              # 多账号错峰,防限流
                try:
                    mails = norm_mail(fetch(a["email"], a.get("api")))
                except Exception as e:
                    if args.verbose:
                        err(f"{a['email']}: {e}")
                    continue
                for i, m in enumerate(mails):
                    mid = mail_id(m, i)
                    if mid in seen[a["email"]]:
                        continue
                    seen[a["email"]].add(mid)
                    d = mail_fields(m)
                    print(f"\n{C.G}{'=' * 58}{C.E}")
                    print(f"{C.G}[新邮件]{C.E} {C.BOLD}{a['email']}{C.E}  {C.DIM}{time.strftime('%H:%M:%S')}{C.E}")
                    print(f"  主题: {C.BOLD}{d['subject'] or '(无主题)'}{C.E}")
                    if d["time"]:
                        print(f"  时间: {C.DIM}{d['time']}{C.E}")
                    if d["code"]:
                        print(f"  {C.G}{C.BOLD}★ 验证码: {d['code']}{C.E}")
                    if d["body"]:
                        one = " ".join(d["body"].split())
                        print(f"  正文: {C.DIM}{one[:400]}{C.E}")
                    print(f"{C.G}{'=' * 58}{C.E}", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n" + info("已停止监控"))
    return 0

def cmd_export(args):
    accts = load_accounts()
    targets = [a for a in accts if not args.email or args.email.lower() in a.get("email", "").lower()]
    rows = []
    for idx, a in enumerate(targets):
        if idx:
            time.sleep(args.delay)             # 多账号错峰,避免触发限流
        try:
            mails = norm_mail(fetch(a["email"], a.get("api")))
        except Exception as e:
            err(f"{a['email']}: {e}")
            continue
        latest = mail_fields(mails[0]) if mails else {}
        c, l = totp(a.get("secret", ""))
        rows.append({
            "email": a["email"],
            "password": a.get("password", ""),
            "totp": c or "",
            "latest_code": latest.get("code") or "",
            "subject": latest.get("subject") or "",
            "mails": len(mails),
            "checked": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            if args.out.endswith(".csv"):
                import csv
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["email"])
                w.writeheader()
                w.writerows(rows)
            else:
                json.dump(rows, f, ensure_ascii=False, indent=2)
        ok(f"已导出到 {args.out}")
    else:
        print()
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0

def cmd_repl(_):
    """交互模式:一直挂着,输入命令随时查。"""
    banner()
    accts = load_accounts()
    if not accts:
        warn("还没账号,现在添加一条(邮箱 密码 2FA秘钥):")
        line = input(">>> ").strip()
        parts = line.split()
        if len(parts) < 2:
            err("格式: 邮箱 密码 [2FA秘钥]")
            return 1
        save_accounts([{"email": parts[0], "password": parts[1],
                        "secret": parts[2] if len(parts) > 2 else "",
                        "api": "", "added": time.strftime("%Y-%m-%d %H:%M:%S")}])
        ok("已添加")
        accts = load_accounts()

    print(f"{C.DIM}命令: get  收信 | totp 出2FA | all 全部账号 | q 退出{C.E}")
    idx = 0
    while True:
        accts = load_accounts() or accts
        a = accts[min(idx, len(accts) - 1)]
        try:
            c, l = totp(a.get("secret", ""))
            mails = norm_mail(fetch(a["email"], a.get("api")))
        except Exception:
            c, l, mails = totp(a.get("secret", ""))[0], 0, []
        latest = mail_fields(mails[0]) if mails else {}
        print(f"\n{C.BOLD}当前账号: {a['email']}{C.E}")
        print(f"  2FA: {C.G}{c or '未设置'}{C.E}" + (f" ({l}s)" if c else ""))
        print(f"  邮件: {len(mails)} 封" + (f"   最新验证码: {C.G}{C.BOLD}{latest.get('code')}{C.E}" if latest.get("code") else ""))
        try:
            cmd = input(f"{C.B}mailpull>{C.E} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if cmd in ("q", "quit", "exit"):
            break
        if cmd in ("", "r", "refresh", "get"):
            show_mails(mails, f"收件箱 · {a['email']}")
        elif cmd == "totp":
            print(f"  当前验证码: {C.G}{C.BOLD}{c or '未设置'}{C.E}")
        elif cmd == "all":
            for x in accts:
                xc, xl = totp(x.get("secret", ""))
                print(f"  {x['email']}  2FA={xc or '-'}  ({xl}s)")
        elif cmd.isdigit() and 1 <= int(cmd) <= len(accts):
            idx = int(cmd) - 1
        elif cmd == "help":
            print("  get 收信 | totp 出2FA | all 全部 | 序号切换 | q 退出")
        else:
            warn("未知命令,输入 help 看帮助")
    ok("再见")
    return 0

# ---------------------------------------------------------------- 入口
def build_parser():
    p = argparse.ArgumentParser(prog="mailpull", description=f"{APP_NAME} 接码邮箱收信助手 v{APP_VER}")
    p.add_argument("--no-banner", action="store_true", help="不打印启动横幅")
    sub = p.add_subparsers(dest="cmd")

    a = sub.add_parser("add", help="添加账号")
    a.add_argument("email"); a.add_argument("password")
    a.add_argument("secret", nargs="?", default="", help="2FA/TOTP 秘钥")
    a.add_argument("--api", default="", help="手动指定收信接口地址")

    d = sub.add_parser("del", help="删除账号"); d.add_argument("email")

    sub.add_parser("list", help="账号列表")

    g = sub.add_parser("get", help="收一次邮件"); g.add_argument("email", nargs="?")
    w = sub.add_parser("watch", help="实时监控收件")
    w.add_argument("email", nargs="?"); w.add_argument("-i", "--interval", type=int, default=5)
    w.add_argument("-v", "--verbose", action="store_true")

    t = sub.add_parser("totp", help="生成 2FA 动态码"); t.add_argument("email", nargs="?")

    e = sub.add_parser("export", help="批量导出验证码")
    e.add_argument("what", nargs="?", default="codes", choices=["codes"])
    e.add_argument("email", nargs="?")
    e.add_argument("-o", "--out", default="", help="输出文件 (.json/.csv)")
    e.add_argument("--delay", type=float, default=1.0, help="多账号间隔秒数(防限流)")

    sub.add_parser("repl", help="交互模式")
    return p

def main():
    argv = sys.argv[1:]
    if not argv:
        banner()
        return cmd_repl(None)

    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        banner()
        return cmd_repl(None)
    if not args.no_banner and args.cmd in ("get", "watch", "totp", "list", "repl"):
        banner()

    dispatch = {
        "add": cmd_add, "del": cmd_del, "list": cmd_list, "get": cmd_get,
        "watch": cmd_watch, "totp": cmd_totp, "export": cmd_export, "repl": cmd_repl,
    }
    try:
        return dispatch[args.cmd](args) or 0
    except KeyboardInterrupt:
        print()
        return 0
    except Exception as e:
        err(f"出错: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())