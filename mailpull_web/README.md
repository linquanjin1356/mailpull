# MailPull Web — 接码邮箱收信助手

用与营销页一致的视觉语言（zinc 色系、`rounded-2xl` 卡片、`ring-1` 描边、明暗双主题）重构的 MailPull 界面。

## 启动

**双击 `启动.bat`** —— 自动起本地服务并打开浏览器。

或命令行：

```bash
python server.py
```

默认端口 `8791`，被占用时自动往后找。服务只监听 `127.0.0.1`，不对外网暴露。

## 界面构成

| 区块 | 说明 |
|---|---|
| 顶栏 | Logo、实时监控开关、明暗切换（sticky + 毛玻璃） |
| 左侧账号卡 | 账号列表，选中项带白底 + ring 高亮，底部添加/删除 |
| 2FA 卡 | 大号等宽验证码 + SVG 倒计时环（每秒刷新）+ 复制按钮 |
| 收件箱卡 | 邮件列表，验证码用琥珀色 chip 高亮，点开看详情，弹窗自动复制 |
| 状态栏 | 底部固定，显示当前操作结果 |

## 为什么需要本地服务

上游收信接口 `https://mail.<域名>/api/fetch` **没有返回 CORS 头**：

```
HTTP/1.1 200 OK
Allow: OPTIONS, HEAD, GET
（无 Access-Control-Allow-Origin）
```

浏览器直接 `fetch` 会被同源策略拦掉。所以由一个本地 Python 服务代请求：

```
浏览器  →  http://127.0.0.1:8791/api/fetch?email=...   （同源，可用）
服务端  →  https://mail.<域名>/api/fetch?email=...     （服务端无跨域限制）
```

服务端还会补 CORS 头回给页面，并把 429 限流做指数退避重试（1.2s → 2.4s → 4.8s）。

## 技术要点

**TOTP 用 Web Crypto API 实现**，不引任何库：

- `crypto.subtle.importKey('raw', key, {name:'HMAC', hash:'SHA-1'})` + `sign()`
- 手动实现 Base32 解码（RFC 4648）
- 已验证：RFC 6238 官方 5 组测试向量全过，且与 Python 实现在同一时间戳输出完全一致

**账号存储**：浏览器 `localStorage` 为主，同时 POST 一份到 `~/.mailpull/accounts.json`，
与命令行版 MailPull 共用同一份账号文件。

**离线可用**：Tailwind 已编译并内联进 `index.html`（31 KB，零外链），断网不影响界面，
只有收信时才需要联网。

## 文件说明

```
mailpull_web/
├── server.py            本地服务：静态托管 + API 代理 + 账号文件读写
├── index.html           成品页面（CSS 已内联，直接托管这个文件）
├── index.src.html       页面源码（含 <!--TAILWIND_CSS--> 占位符）
├── app.js               前端逻辑：账号/TOTP/收信/复制/监控
├── build.py             重建：编译 Tailwind 并内联进页面
├── tw.config.js         Tailwind 配置（darkMode: class）
├── tw.input.css         Tailwind 入口
├── verify_totp.js       TOTP 算法自测（RFC 6238 向量）
└── 启动.bat             一键启动
```

改完样式（`index.src.html` 的 class）后重新构建：

```bash
python build.py
```

## 打包成 exe（客户不用装 Python）

```bash
pyinstaller -F --clean --name MailPull-Web \
  --icon=../logo.ico \
  --version-file=version_info_web.txt \
  --add-data "index.html;." \
  --add-data "app.js;." \
  server.py
```

产出 `dist/MailPull-Web.exe`（约 8.7 MB），双击即启动服务并自动开浏览器。

关键点：`server.py` 里做了 frozen 判断，打包后静态资源从 `sys._MEIPASS` 读取：

```python
if getattr(sys, "frozen", False):
    HERE = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
```

不做这个判断，exe 启动后访问页面会 404——因为 PyInstaller 会把 `--add-data` 的文件解压到临时目录，
而不是 exe 所在目录。

`--add-data` 的分隔符：Windows 用 `;`，macOS/Linux 用 `:`。

## 与命令行版的关系

两个版本共用 `~/.mailpull/accounts.json`：

- 命令行版 `mailpull.py`（Python，可打包 exe，纯终端）
- Web 版 `server.py`（浏览器界面，视觉更强）

在任一版本添加的账号，另一版本都能读到。
