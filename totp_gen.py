import base64, hashlib, hmac, struct, time, sys, os

# 秘钥从环境变量读取：MAILPULL_SECRET
SECRET = os.environ.get("MAILPULL_SECRET", "")

if not SECRET:
    raise SystemExit("请先设置环境变量 MAILPULL_SECRET（Base32 秘钥）")

def base32_decode(s):
    s = s.upper().replace("=", "")
    # pad to multiple of 8
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
    return code, (30 - (t % 30))

now = int(time.time())
code, remain = totp(SECRET, now)
print(f"当前时间(UTC): {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now))}")
print(f"当前 TOTP: {code:06d}  (剩余 {remain} 秒)")
# 也给出下一个周期参考
nxt = now + 30
code2, _ = totp(SECRET, nxt)
print(f"下一周期 TOTP: {code2:06d}")
