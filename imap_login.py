import base64, hashlib, hmac, struct, time, imaplib, ssl, sys, os

# 凭据从环境变量读取，不写死在代码里
HOST = os.environ.get("MAILPULL_HOST", "")
PORT = 993
EMAIL = os.environ.get("MAILPULL_EMAIL", "")
PASSWORD = os.environ.get("MAILPULL_PASSWORD", "")
SECRET = os.environ.get("MAILPULL_SECRET", "")

def base32_decode(s):
    s = s.upper().replace("=", "")
    pad = (-len(s)) % 8
    s += "=" * pad
    return base64.b32decode(s)

def totp(secret, t=None):
    if t is None:
        t = int(time.time())
    key = base32_decode(secret)
    counter = t // 30
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[-1] & 0x0F
    code = (struct.unpack(">I", h[o:o+4])[0] & 0x7FFFFFFF) % 1000000
    return code

code = totp(SECRET)
print(f"当前 TOTP: {code:06d}")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 尝试多种认证组合
attempts = [
    ("password only", PASSWORD),
    ("password+otp (no sep)", PASSWORD + f"{code:06d}"),
    ("password+otp (with space)", PASSWORD + " " + f"{code:06d}"),
    ("otp only", f"{code:06d}"),
]

for label, pwd in attempts:
    try:
        M = imaplib.IMAP4_SSL(HOST, PORT, ssl_context=ctx)
        M.login(EMAIL, pwd)
        print(f"[OK] {label} -> 登录成功")
        typ, data = M.select("INBOX")
        print(f"     INBOX: {typ}, messages={data[0] if data and data[0] else '?'}")
        M.logout()
        break
    except imaplib.IMAP4.error as e:
        print(f"[FAIL] {label} -> {e}")
    except Exception as e:
        print(f"[ERR]  {label} -> {type(e).__name__}: {e}")
