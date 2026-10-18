#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MailPull Web — 本地服务
================================================
做两件事:
  1. 托管前端页面(index.html)
  2. 反向代理收信接口 —— 上游 mail.<域名>/api/fetch 没有 CORS 头，
     浏览器直连会被拦，所以必须由服务端代请求再回给页面

只监听 127.0.0.1，不对外暴露。
"""

import json
import os
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# PyInstaller 打包成 exe 后，静态资源会被解压到临时目录 sys._MEIPASS，
# 源码运行时则用脚本所在目录。两种模式都要能正确找到 index.html / app.js。
if getattr(sys, "frozen", False):
    HERE = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    HERE = os.path.dirname(os.path.abspath(__file__))

PORT = int(os.environ.get("MAILPULL_PORT", "8791"))
ACCOUNT_FILE = os.path.join(os.path.expanduser("~"), ".mailpull", "accounts.json")

# 上游证书不可控，跳过校验（仅本地工具，不外发数据）
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

UA = "MailPull-Web/1.0"


def guess_upstream(email, override=""):
    """由邮箱域名推导收信接口地址。"""
    if override:
        return override.rstrip("/")
    domain = email.split("@")[-1].strip().lower()
    return f"https://mail.{domain}/api/fetch"


def upstream_fetch(email, api="", retries=3):
    """
    服务端请求上游接口，返回 (status, dict|str)。
    上游有频率限制(429)，这里做指数退避重试：1.2s → 2.4s → 4.8s
    """
    url = guess_upstream(email, api)
    sep = "&" if "?" in url else "?"
    full = f"{url}{sep}email={urllib.parse.quote(email)}"
    last = ""

    for attempt in range(retries):
        req = urllib.request.Request(
            full, headers={"User-Agent": UA, "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=20, context=_CTX) as r:
                raw = r.read().decode("utf-8", "replace")
            try:
                return 200, json.loads(raw)
            except json.JSONDecodeError:
                return 502, {"error": "上游返回的不是合法 JSON"}
        except urllib.error.HTTPError as e:
            # 429 限流 / 5xx 服务端错误 → 退避重试
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(1.2 * (2 ** attempt))
                last = f"上游返回 {e.code}"
                continue
            msg = "请求过于频繁，请稍后再试（上游限流）" if e.code == 429 else f"上游返回 {e.code}"
            return e.code, {"error": msg}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.2 * (2 ** attempt))
                last = str(e)
                continue
            return 502, {"error": f"连接失败: {e}"}

    return 502, {"error": f"重试 {retries} 次仍失败: {last}"}


def load_accounts():
    if not os.path.exists(ACCOUNT_FILE):
        return []
    try:
        with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception:
        return []


def save_accounts(accts):
    os.makedirs(os.path.dirname(ACCOUNT_FILE), exist_ok=True)
    tmp = ACCOUNT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(accts, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ACCOUNT_FILE)
    try:
        os.chmod(ACCOUNT_FILE, 0o600)
    except Exception:
        pass


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    # 静默日志，避免控制台刷屏
    def log_message(self, fmt, *args):
        if os.environ.get("MAILPULL_VERBOSE"):
            super().log_message(fmt, *args)

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        # --- 收信代理 ---
        if path == "/api/fetch":
            email = (qs.get("email") or [""])[0].strip()
            api = (qs.get("api") or [""])[0].strip()
            if not email or "@" not in email:
                return self._json({"error": "缺少有效 email 参数"}, 400)
            status, data = upstream_fetch(email, api)
            return self._json(data, 200 if status == 200 else status)

        # --- 账号读写 ---
        if path == "/api/accounts":
            return self._json({"accounts": load_accounts()})

        # --- 健康检查 ---
        if path == "/api/ping":
            return self._json({"ok": True, "version": "1.0.0"})

        # --- 静态页面 ---
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            return self._json({"error": "请求体不是合法 JSON"}, 400)

        if parsed.path == "/api/accounts":
            # 整体覆盖写入
            accts = payload.get("accounts")
            if not isinstance(accts, list):
                return self._json({"error": "accounts 必须是数组"}, 400)
            save_accounts(accts)
            return self._json({"ok": True, "count": len(accts)})

        return self._json({"error": "not found"}, 404)

    def end_headers(self):
        # 静态资源禁缓存，改完刷新立即生效
        if self.path.endswith((".html", ".css", ".js")):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()


def find_port(start):
    """从 start 开始找一个空闲端口。"""
    import socket
    for p in range(start, start + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError("找不到可用端口")


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    port = find_port(PORT)
    url = f"http://127.0.0.1:{port}"

    print("=" * 54)
    print("  MailPull Web — 接码邮箱收信助手")
    print("=" * 54)
    print(f"  服务地址: {url}")
    print(f"  账号文件: {ACCOUNT_FILE}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 54)

    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()