#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接码邮箱收信 + TOTP 2FA 一体化工具（调试脚本）

凭据不写死在代码里，从环境变量读取：
  MAILPULL_EMAIL / MAILPULL_PASSWORD / MAILPULL_SECRET

用法:
  python mail_client.py once      # 查一次邮件
  python mail_client.py watch     # 持续监控, 新邮件自动显示验证码
  python mail_client.py totp      # 只显示当前 TOTP 验证码
"""
import base64, hashlib, hmac, struct, time, sys, json, urllib.request, ssl, os

EMAIL = os.environ.get("MAILPULL_EMAIL", "")
PASSWORD = os.environ.get("MAILPULL_PASSWORD", "")
SECRET = os.environ.get("MAILPULL_SECRET", "")


def api_url(email):
    """由邮箱域名推导收信接口。"""
    return f"https://mail.{email.split('@')[-1]}/api/fetch"

def base32_decode(s):
    s = s.upper().replace("=", "")
    s += "=" * ((-len(s)) % 8)
    return base64.b32decode(s)

def totp(secret, t=None):
    if t is None:
        t = int(time.time())
    key = base32_decode(secret)
    msg = struct.pack(">Q", t // 30)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return f"{(struct.unpack('>I', h[o:o+4])[0] & 0x7FFFFFFF) % 1000000:06d}", 30 - (t % 30)

def fetch_mails():
    if not EMAIL or "@" not in EMAIL:
        raise SystemExit("请先设置环境变量 MAILPULL_EMAIL")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    url = f"{api_url(EMAIL)}?email={EMAIL}"
    req = urllib.request.Request(url, headers={"User-Agent": "MailPull/1.0"})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))

def show_code(data):
    code = data.get("code")
    codes = data.get("codes")
    emails = data.get("emails") or []
    print(f"[{time.strftime('%H:%M:%S')}] 邮箱 {data.get('email')}  邮件数: {len(emails)}")
    if code:
        print(f"    最新验证码: {code}")
    if emails:
        for m in emails:
            subj = m.get("subject") or "(无主题)"
            body = m.get("body") or m.get("body_preview") or ""
            print(f"    - {subj}")
            if body:
                print(f"      正文: {body[:300]}")
    return emails

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    if mode == "totp":
        c, remain = totp(SECRET)
        print(f"当前 TOTP: {c}  (剩余 {remain} 秒)")
        print(f"账号: {EMAIL}\n密码: {PASSWORD}")
        return
    if mode == "watch":
        seen = set()
        print(f"开始监控 {EMAIL} ... Ctrl+C 停止")
        while True:
            try:
                data = fetch_mails()
                emails = data.get("emails") or []
                for m in emails:
                    uid = m.get("uid") or m.get("id") or json.dumps(m, ensure_ascii=False)
                    if uid not in seen:
                        seen.add(uid)
                        subj = m.get("subject") or "(无主题)"
                        body = m.get("body") or m.get("body_preview") or ""
                        code = m.get("code") or (m.get("codes") or [None])[0]
                        print(f"\n>>> 新邮件 [{time.strftime('%H:%M:%S')}]: {subj}")
                        if code:
                            print(f">>> 验证码: {code}")
                        if body:
                            print(f">>> 正文: {body[:500]}")
            except Exception as e:
                print(f"查询失败: {e}")
            time.sleep(5)
    else:
        show_code(fetch_mails())

if __name__ == "__main__":
    main()
