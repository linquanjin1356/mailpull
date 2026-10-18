// 用 Node 的 WebCrypto 跑 app.js 里同一套 TOTP 算法，输出固定时间点的码，
// 再和 Python 实现对比，确保前端算出来的码和手机验证器一致。
const { webcrypto } = require("node:crypto");
const crypto = webcrypto;

const B32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

function b32decode(secret) {
  const s = String(secret || "").toUpperCase().replace(/[\s\-_=]/g, "");
  let bits = 0, val = 0;
  const out = [];
  for (const ch of s) {
    const idx = B32.indexOf(ch);
    if (idx < 0) throw new Error("bad char");
    val = (val << 5) | idx;
    bits += 5;
    if (bits >= 8) { out.push((val >>> (bits - 8)) & 0xff); bits -= 8; }
  }
  return new Uint8Array(out);
}

async function totp(secret, ts, period = 30, digits = 6) {
  const key = await crypto.subtle.importKey(
    "raw", b32decode(secret), { name: "HMAC", hash: "SHA-1" }, false, ["sign"]
  );
  const counter = Math.floor(Math.floor(ts / 1000) / period);
  const buf = new ArrayBuffer(8);
  const dv = new DataView(buf);
  dv.setUint32(0, Math.floor(counter / 4294967296));
  dv.setUint32(4, counter >>> 0);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, buf));
  const off = sig[sig.length - 1] & 0x0f;
  const bin = ((sig[off] & 0x7f) << 24) | (sig[off+1] << 16) | (sig[off+2] << 8) | sig[off+3];
  return String(bin % 10 ** digits).padStart(digits, "0");
}

(async () => {
  // RFC 6238 官方测试向量（密钥 "12345678901234567890"）
  const vSecret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ";
  const vectors = [
    [59000, "287082"], [1111111109000, "081804"],
    [1111111111000, "050471"], [1234567890000, "005924"],
    [2000000000000, "279037"],
  ];
  let pass = 0;
  console.log("=== RFC 6238 官方测试向量（WebCrypto 实现） ===");
  for (const [ts, expect] of vectors) {
    const got = await totp(vSecret, ts);
    const ok = got === expect;
    if (ok) pass++;
    console.log(`  t=${String(ts).padEnd(14)} 期望 ${expect}  实际 ${got}  ${ok ? "OK" : "FAIL"}`);
  }
  console.log(`\n向量通过: ${pass}/${vectors.length}`);

  // 输出示例账号在固定时间点的码，供 Python 对比
  // 这里用的是公开的测试秘钥，不是任何真实账号
  const demo = "JBSWY3DPEHPK3PXP";
  console.log("\n=== 示例账号固定时间点（供 Python 交叉核对） ===");
  for (const ts of [1792300000000, 1792312345000, 1792399999000]) {
    console.log(`  ts=${ts}  ->  ${await totp(demo, ts)}`);
  }
})();