/* ============================================================
   MailPull Web — 前端逻辑
   账号存 localStorage，同时同步一份到本地服务(~/.mailpull/accounts.json)
   收信走后端 /api/fetch 代理（上游无 CORS 头，浏览器不能直连）
   ============================================================ */

const $ = (id) => document.getElementById(id);
const LS_ACCOUNTS = "mailpull.accounts";
const LS_CUR = "mailpull.current";
const LS_THEME = "mailpull.theme";

const state = {
  accounts: [],
  cur: -1,
  mails: [],
  seen: new Set(),
  watching: false,
  watchTimer: null,
  tickTimer: null,
  lastCode: "",
};

/* ---------------- 主题 ---------------- */
function applyTheme() {
  const dark = document.documentElement.classList.contains("dark");
  $("iconSun").classList.toggle("hidden", dark);
  $("iconMoon").classList.toggle("hidden", !dark);
}
(function initTheme() {
  let t = null;
  try { t = localStorage.getItem(LS_THEME); } catch (e) {}
  const prefers = window.matchMedia("(prefers-color-scheme: dark)").matches;
  if (t === "dark" || (!t && prefers)) document.documentElement.classList.add("dark");
})();
$("themeBtn").addEventListener("click", () => {
  const next = !document.documentElement.classList.contains("dark");
  document.documentElement.classList.toggle("dark", next);
  try { localStorage.setItem(LS_THEME, next ? "dark" : "light"); } catch (e) {}
  applyTheme();
});

/* ---------------- 账号存储 ---------------- */
function loadAccounts() {
  try {
    const raw = localStorage.getItem(LS_ACCOUNTS);
    if (raw) return JSON.parse(raw) || [];
  } catch (e) {}
  return [];
}

function persistAccounts() {
  try { localStorage.setItem(LS_ACCOUNTS, JSON.stringify(state.accounts)); } catch (e) {}
  // 备份到本地文件，和命令行版共用
  fetch("/api/accounts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accounts: state.accounts }),
  }).catch(() => {});
}

async function hydrateFromServer() {
  // 本地没有账号时，尝试从 ~/.mailpull/accounts.json 导入（兼容命令行版）
  if (state.accounts.length) return;
  try {
    const r = await fetch("/api/accounts");
    const d = await r.json();
    if (Array.isArray(d.accounts) && d.accounts.length) {
      state.accounts = d.accounts;
      persistAccounts();
    }
  } catch (e) {}
}

/* ---------------- TOTP (Web Crypto) ---------------- */
const B32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

function b32decode(secret) {
  const s = String(secret || "").toUpperCase().replace(/[\s\-_=]/g, "");
  if (!s) throw new Error("秘钥为空");
  let bits = 0, val = 0;
  const out = [];
  for (const ch of s) {
    const idx = B32.indexOf(ch);
    if (idx < 0) throw new Error("秘钥含非法字符");
    val = (val << 5) | idx;
    bits += 5;
    if (bits >= 8) {
      out.push((val >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }
  if (!out.length) throw new Error("秘钥无效");
  return new Uint8Array(out);
}

async function totp(secret, period = 30, digits = 6, ts = Date.now()) {
  let keyBytes;
  try {
    keyBytes = b32decode(secret);
  } catch (e) {
    return null;
  }
  const key = await crypto.subtle.importKey(
    "raw", keyBytes, { name: "HMAC", hash: "SHA-1" }, false, ["sign"]
  );
  const counter = Math.floor(Math.floor(ts / 1000) / period);
  const buf = new ArrayBuffer(8);
  const dv = new DataView(buf);
  dv.setUint32(0, Math.floor(counter / 4294967296));
  dv.setUint32(4, counter >>> 0);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, buf));
  const off = sig[sig.length - 1] & 0x0f;
  const bin =
    ((sig[off] & 0x7f) << 24) |
    (sig[off + 1] << 16) |
    (sig[off + 2] << 8) |
    sig[off + 3];
  return String(bin % 10 ** digits).padStart(digits, "0");
}

/* ---------------- 验证码提取 ---------------- */
const LABELED = [
  /(?:验证码|校验码|动态码|安全码|驗證碼|动态密码|一次性密码|随机码|口令|登录码)\s*(?:是|为)?\s*[:：]?\s*(?:code\s*[:：]\s*)?([0-9]{4,8})/i,
  /(?:verification|verify|security|confirmation|login|one[-\s]?time)\s*(?:code|password|pin)\s*(?:is)?\s*[:：]?\s*([0-9]{4,8})/i,
  /\botp\b\s*(?:is)?\s*[:：]?\s*([0-9]{4,8})/i,
  /(?:验证码|驗證碼|code|otp|pin)\s*(?:is|是|为)?\s*[:：]?\s*([A-Z0-9]{6,8})\b/i,
];

function extractCode(subject, body) {
  const text = `${subject || ""}\n${body || ""}`;
  for (const re of LABELED) {
    const m = text.match(re);
    if (m && m[1]) return m[1];
  }
  // 兜底：清掉噪声再找孤立 6 位
  let clean = text
    .replace(/https?:\/\/\S+/g, " ")
    .replace(/\b[\w.-]+@[\w.-]+\.\w+\b/g, " ")
    .replace(/\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?/g, " ")
    .replace(/\d{1,2}:\d{2}(:\d{2})?/g, " ")
    .replace(/(?<!\d)\d{11,}(?!\d)/g, " ");
  const m = clean.match(/(?<![\w-])([0-9]{6})(?![\w-])/);
  return m ? m[1] : null;
}

/* ---------------- 邮件字段归一 ---------------- */
function pick(o, keys, dflt = "") {
  for (const k of keys) {
    if (o && o[k] !== undefined && o[k] !== null && o[k] !== "") return o[k];
  }
  return dflt;
}

function normMail(m) {
  const subject = String(pick(m, ["subject", "title", "sub"]) || "").trim();
  let body = pick(m, ["body", "body_preview", "text", "content", "preview", "snippet"]);
  if (body && typeof body === "object") body = body.text || body.html || "";
  body = String(body || "");
  if (body.includes("<") && body.includes(">")) body = body.replace(/<[^>]+>/g, " ");
  const time = pick(m, ["date", "time", "received_at", "datetime"]);
  let code = pick(m, ["code"], null);
  if (!code && Array.isArray(m.codes) && m.codes.length) code = m.codes[0];
  if (!code) code = extractCode(subject, body);
  return { subject, body, time, code, id: pick(m, ["uid", "id", "message_id"], null) };
}

function normList(data) {
  if (Array.isArray(data)) return data;
  if (!data || typeof data !== "object") return [];
  for (const k of ["emails", "mails", "messages", "data", "items", "list", "results"]) {
    if (Array.isArray(data[k])) return data[k];
  }
  return [];
}

/* ---------------- 渲染 ---------------- */
function setStatus(msg) {
  $("status").textContent = msg;
}

function renderAccounts() {
  const box = $("acctList");
  box.innerHTML = "";
  $("acctCount").textContent = state.accounts.length;
  $("acctEmpty").classList.toggle("hidden", state.accounts.length > 0);

  state.accounts.forEach((a, i) => {
    const active = i === state.cur;
    const el = document.createElement("button");
    el.type = "button";
    el.className =
      "group flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left text-xs transition-all " +
      (active
        ? "bg-white text-zinc-900 ring-1 ring-zinc-300 dark:bg-zinc-800 dark:text-white dark:ring-zinc-600"
        : "text-zinc-600 hover:bg-white hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white");

    const dot = document.createElement("span");
    dot.className =
      "h-1.5 w-1.5 shrink-0 rounded-full " +
      (active ? "bg-emerald-500" : "bg-zinc-300 dark:bg-zinc-600");

    const txt = document.createElement("span");
    txt.className = "truncate font-medium";
    txt.textContent = a.email;

    el.append(dot, txt);
    el.addEventListener("click", () => selectAccount(i));
    box.appendChild(el);
  });
}

async function renderTotp() {
  const a = state.accounts[state.cur];
  if (!a || !a.secret) {
    $("totpCode").textContent = a ? "未设置 2FA" : "—— —— ——";
    $("totpMeta").textContent = a ? "添加账号时填入秘钥即可启用" : "选择账号后显示";
    $("ringText").textContent = "--";
    $("ring").setAttribute("stroke-dashoffset", "263.9");
    state.lastCode = "";
    return;
  }
  const code = await totp(a.secret);
  if (!code) {
    $("totpCode").textContent = "秘钥无效";
    $("totpMeta").textContent = "检查是否复制完整";
    return;
  }
  state.lastCode = code;
  $("totpCode").textContent = `${code.slice(0, 3)} ${code.slice(3)}`;
  const left = 30 - (Math.floor(Date.now() / 1000) % 30);
  $("totpMeta").textContent = `${left} 秒后刷新 · 秘钥长度 ${String(a.secret).replace(/\s/g, "").length}`;
  $("ringText").textContent = left;
  $("ring").setAttribute("stroke-dashoffset", String(263.9 * (1 - left / 30)));
}

function renderMails() {
  const list = $("mailList");
  list.innerHTML = "";
  $("mailCount").textContent = `${state.mails.length} 封`;
  $("mailEmpty").classList.toggle("hidden", state.mails.length > 0);

  state.mails.forEach((raw, i) => {
    const d = normMail(raw);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className =
      "flex w-full items-start gap-3 rounded-xl px-3.5 py-3 text-left transition-colors hover:bg-white dark:hover:bg-zinc-800";

    const main = document.createElement("div");
    main.className = "min-w-0 flex-1";

    const subj = document.createElement("p");
    subj.className = "truncate text-sm font-medium text-zinc-900 dark:text-white";
    subj.textContent = d.subject || "(无主题)";

    const meta = document.createElement("p");
    meta.className = "mt-0.5 truncate text-[11px] text-zinc-500 dark:text-zinc-400";
    meta.textContent = d.time || "";

    main.append(subj, meta);
    btn.appendChild(main);

    if (d.code) {
      const chip = document.createElement("span");
      chip.className =
        "shrink-0 rounded-lg bg-amber-50 px-2.5 py-1 font-mono text-xs font-bold text-amber-900 ring-1 ring-inset ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-500/30";
      chip.textContent = d.code;
      btn.appendChild(chip);
    }

    btn.addEventListener("click", () => showDetail(raw));
    list.appendChild(btn);
  });
}

function showDetail(raw) {
  const d = normMail(raw);
  $("dSubject").textContent = d.subject || "(无主题)";
  $("dTime").textContent = d.time || "";
  $("dBody").textContent = d.body || "";
  $("detailWrap").classList.remove("hidden");
  $("dCopy").onclick = () => copyText(d.code);
  if (d.code) copyText(d.code, true);
}

/* ---------------- 复制 ---------------- */
async function copyText(text, silent) {
  if (!text) {
    setStatus("没有可复制的验证码");
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    setStatus(`已复制: ${text}`);
  } catch (e) {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); setStatus(`已复制: ${text}`); } catch (_) {}
    ta.remove();
  }
}

/* ---------------- 收信 ---------------- */
async function fetchMails(silent) {
  const a = state.accounts[state.cur];
  if (!a) {
    if (!silent) setStatus("请先添加一个邮箱账号");
    return;
  }
  if (!silent) setStatus("正在收取邮件…");
  try {
    const qs = new URLSearchParams({ email: a.email });
    if (a.api) qs.set("api", a.api);
    const r = await fetch(`/api/fetch?${qs}`);
    const data = await r.json();
    if (data.error) {
      setStatus(`收取失败: ${data.error}`);
      return;
    }
    const list = normList(data);
    const isNew = list.length > state.mails.length;

    state.mails = list;
    renderMails();

    // 新邮件提示
    if (isNew && state.mails.length) {
      const d = normMail(state.mails[0]);
      document.querySelectorAll("#mailList > button").forEach((b, i) => {
        if (i === 0) b.classList.add("bg-white", "dark:bg-zinc-800");
      });
      setStatus(`收到新邮件: ${d.subject || "(无主题)"}` + (d.code ? `　验证码 ${d.code}` : ""));
      if (d.code) {
        try { new AudioContext().resume(); } catch (e) {}
      }
    } else if (!silent) {
      setStatus(`收取完成，共 ${list.length} 封邮件`);
    }
  } catch (e) {
    setStatus(`收取失败: ${e.message}`);
  }
}

/* ---------------- 账号操作 ---------------- */
function selectAccount(i) {
  state.cur = i;
  try { localStorage.setItem(LS_CUR, String(i)); } catch (e) {}
  state.mails = [];
  renderAccounts();
  renderMails();
  $("detailWrap").classList.add("hidden");
  renderTotp();
  fetchMails(true);
}

function openModal() {
  $("inEmail").value = "";
  $("inPass").value = "";
  $("inKey").value = "";
  $("inApi").value = "";
  $("modalTip").textContent = "";
  $("modal").classList.remove("hidden");
  $("modal").classList.add("flex");
  setTimeout(() => $("inEmail").focus(), 50);
}

function closeModal() {
  $("modal").classList.add("hidden");
  $("modal").classList.remove("flex");
}

async function addAccount() {
  const email = $("inEmail").value.trim();
  const pass = $("inPass").value.trim();
  const key = $("inKey").value.trim();
  const api = $("inApi").value.trim();
  const tip = $("modalTip");

  if (!email || !email.includes("@")) {
    tip.className = "mt-3 min-h-[16px] text-xs text-red-600 dark:text-red-400";
    tip.textContent = "邮箱格式不对，应为 user@example.com";
    return;
  }
  if (!pass) {
    tip.className = "mt-3 min-h-[16px] text-xs text-red-600 dark:text-red-400";
    tip.textContent = "密码不能为空";
    return;
  }

  const rec = { email, password: pass, secret: key, api };
  state.accounts = state.accounts.filter((a) => a.email.toLowerCase() !== email.toLowerCase());
  state.accounts.push(rec);
  persistAccounts();

  closeModal();
  state.cur = state.accounts.length - 1;
  renderAccounts();
  renderTotp();
  fetchMails(true);

  if (key) {
    const c = await totp(key);
    setStatus(c ? `已添加 ${email}　2FA 秘钥有效: ${c}` : `已添加 ${email}　2FA 秘钥无效`);
  } else {
    setStatus(`已添加 ${email}`);
  }
}

function delAccount() {
  const a = state.accounts[state.cur];
  if (!a) {
    setStatus("请先选择一个账号");
    return;
  }
  if (!confirm(`确定删除账号 ${a.email} ?`)) return;
  state.accounts.splice(state.cur, 1);
  state.cur = state.accounts.length ? 0 : -1;
  state.mails = [];
  persistAccounts();
  renderAccounts();
  renderMails();
  renderTotp();
  $("detailWrap").classList.add("hidden");
  setStatus("账号已删除");
}

/* ---------------- 实时监控 ---------------- */
function toggleWatch() {
  state.watching = !state.watching;
  if (state.watching) {
    $("watchDot").className = "h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse";
    $("watchText").textContent = "监控中";
    setStatus("实时监控已开启，每 5 秒检查一次");
    fetchMails(true);
    state.watchTimer = setInterval(() => fetchMails(true), 5000);
  } else {
    $("watchDot").className = "h-1.5 w-1.5 rounded-full bg-zinc-400 dark:bg-zinc-600";
    $("watchText").textContent = "实时监控";
    setStatus("实时监控已停止");
    clearInterval(state.watchTimer);
  }
}

/* ---------------- 事件绑定 ---------------- */
$("addBtn").addEventListener("click", openModal);
$("delBtn").addEventListener("click", delAccount);
$("mCancel").addEventListener("click", closeModal);
$("mOk").addEventListener("click", addAccount);
$("fetchBtn").addEventListener("click", () => fetchMails(false));
$("watchBtn").addEventListener("click", toggleWatch);
$("copyTotp").addEventListener("click", () => copyText(state.lastCode));
$("clearAcct").addEventListener("click", () => {
  renderTotp();
  setStatus("已刷新");
});

// 粘贴 `邮箱----密码----秘钥` 自动拆分
$("inEmail").addEventListener("input", (e) => {
  const v = e.target.value;
  if (v.includes("----")) {
    const p = v.split("----").map((x) => x.trim());
    $("inEmail").value = p[0] || "";
    $("inPass").value = p[1] || "";
    $("inKey").value = p[2] || "";
  }
});

$("modal").addEventListener("click", (e) => {
  if (e.target === $("modal")) closeModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
  if (e.key === "Enter" && !$("modal").classList.contains("hidden")) addAccount();
});

/* ---------------- 启动 ---------------- */
(async function boot() {
  // ?reset=1 —— 一键清空浏览器本地保存的账号数据
  // （账号同时存在 localStorage，删服务器文件删不掉浏览器里那份）
  if (new URLSearchParams(location.search).get("reset") === "1") {
    try {
      localStorage.removeItem("mailpull.accounts");
      localStorage.removeItem("mailpull.current");
      localStorage.removeItem("mailpull.theme");
    } catch (e) {}
    // 同时清空服务端的 accounts.json，否则下面的 hydrateFromServer 会把它导回来
    try {
      await fetch("/api/accounts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accounts: [] }),
      });
    } catch (e) {}
    history.replaceState(null, "", "/");
  }

  applyTheme();
  state.accounts = loadAccounts();
  await hydrateFromServer();
  if (!state.accounts.length) {
    state.cur = -1;
  } else {
    let saved = 0;
    try { saved = parseInt(localStorage.getItem(LS_CUR) || "0", 10) || 0; } catch (e) {}
    state.cur = Math.min(Math.max(saved, 0), state.accounts.length - 1);
  }
  renderAccounts();
  renderMails();
  renderTotp();

  // 每秒刷新 2FA 倒计时
  state.tickTimer = setInterval(() => {
    if (state.accounts[state.cur]) renderTotp();
  }, 1000);

  if (state.accounts.length) {
    fetchMails(true);
    setStatus("就绪");
  } else {
    setStatus("请先添加账号");
  }
})();