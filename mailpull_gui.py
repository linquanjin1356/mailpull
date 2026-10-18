#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MailPull GUI — 接码邮箱收信助手 图形界面版
================================================
零第三方依赖(仅 tkinter + 标准库),可直接打包成 exe。

功能:
  · 图形化管理多个接码邮箱账号
  · 大号显示 2FA 动态码,带倒计时进度条,一键复制
  · 收件箱列表,自动提取并高亮验证码,一键复制
  · 实时监控模式,新邮件自动刷新并提示
  · 批量导出所有账号的验证码到 CSV/JSON
"""

import os
import sys
import time
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import mailpull as mp

# ---------------------------------------------------------------- 主题配色
BG      = "#12141c"
CARD    = "#1c1f2b"
CARD_HI = "#252936"
LINE    = "#2f3444"
TEXT    = "#e6e8ef"
TEXT_DIM= "#8b90a3"
ACCENT  = "#3b82f6"
ACC_DK  = "#2563eb"
GREEN   = "#10b981"
RED     = "#ef4444"
AMBER   = "#f59e0b"
CODE_BG = "#fff8e1"
CODE_FG = "#111827"

def pick_font(family_default, size, weight="normal"):
    """挑一个系统里存在的中文字体。"""
    try:
        import tkinter.font as tkfont
        avail = set(tkfont.families())
    except Exception:
        avail = set()
    for f in ("Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC",
              "Hiragino Sans GB", "Noto Sans CJK SC", "WenQuanYi Micro Hei", "sans-serif"):
        if f in avail:
            return (f, size, weight)
    return (family_default, size, weight)

F_BIG   = pick_font("TkDefaultFont", 30, "bold")
F_MID   = pick_font("TkDefaultFont", 15, "bold")
F_NORM  = pick_font("TkDefaultFont", 10)
F_SMALL = pick_font("TkDefaultFont", 9)
F_TITLE = pick_font("TkDefaultFont", 14, "bold")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("MailPull — 接码邮箱收信助手")
        self.root.geometry("1060x720")
        self.root.configure(bg=BG)
        self._set_icon()
        self._center()

        self.accounts = mp.load_accounts()
        self.cur = 0
        self.q = queue.Queue()
        self.watching = False
        self.remain = 0
        self.seen = set()

        self._style()
        self._build()
        self._sync_accounts()
        self.refresh_totp()
        self.root.after(1000, self._tick)
        self.root.after(80, self._drain)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    # ------------------------------------------------------------ 基础
    def _set_icon(self):
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.ico")
        if os.path.exists(p):
            try:
                self.root.iconbitmap(p)
            except Exception:
                pass

    def _center(self):
        self.root.update_idletasks()
        w, h = 1060, 720
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure(".", background=BG, foreground=TEXT,
                    fieldbackground=CARD, bordercolor=LINE, focuscolor=ACCENT)
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=CARD)
        s.configure("TLabel", background=BG, foreground=TEXT, font=F_NORM)
        s.configure("Card.TLabel", background=CARD, foreground=TEXT)
        s.configure("Dim.TLabel", background=BG, foreground=TEXT_DIM, font=F_SMALL)
        s.configure("CardDim.TLabel", background=CARD, foreground=TEXT_DIM, font=F_SMALL)
        s.configure("Head.TLabel", background=BG, foreground=TEXT, font=F_TITLE)
        s.configure("TButton", background=CARD_HI, foreground=TEXT, font=F_NORM,
                    borderwidth=0, focusthickness=0, padding=(14, 8))
        s.configure("TButton:hover", background=LINE)
        s.configure("Acc.TButton", background=ACCENT, foreground="#ffffff")
        s.configure("Acc.TButton:hover", background=ACC_DK)
        s.configure("Green.TButton", background=GREEN, foreground="#ffffff")
        s.configure("Green.TButton:hover", background="#059669")
        s.configure("Red.TButton", background="#3a1f26", foreground="#fca5a5")
        s.configure("Red.TButton:hover", background=RED)
        s.configure("TEntry", fieldbackground=BG, foreground=TEXT, insertbackground=TEXT,
                    bordercolor=LINE, lightcolor=LINE, darkcolor=LINE, padding=8)
        s.configure("TProgressbar", troughcolor=CARD_HI, background=ACCENT,
                    bordercolor=CARD_HI, lightcolor=ACCENT, darkcolor=ACCENT)
        s.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
                    rowheight=34, font=F_NORM, borderwidth=0)
        s.configure("Treeview.Heading", background=CARD_HI, foreground=TEXT_DIM,
                    font=F_SMALL, relief="flat")
        s.map("Treeview", background=[("selected", ACC_DK)], foreground=[("selected", "#ffffff")])

    def _mk(self, parent, **kw):
        return tk.Frame(parent, bg=kw.pop("bg", BG), **kw)

    # ------------------------------------------------------------ 布局
    def _build(self):
        self._build_top()
        self._build_body()
        self._build_bottom()

    def _build_top(self):
        top = tk.Frame(self.root, bg=CARD, height=62, highlightthickness=0)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)
        tk.Label(top, text="MailPull", bg=CARD, fg=TEXT, font=pick_font("TkDefaultFont", 17, "bold")).pack(side="left", padx=(20, 6))
        tk.Label(top, text="接码邮箱收信助手", bg=CARD, fg=TEXT_DIM, font=F_NORM).pack(side="left")

        self.watch_btn = ttk.Button(top, text="▶  实时监控", style="Green.TButton",
                                    command=self.toggle_watch)
        self.watch_btn.pack(side="right", padx=(6, 16), pady=14)

        tk.Frame(self.root, bg=LINE, height=1).pack(fill="x")

    def _build_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=14)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_right(body)

    # ---- 左:账号列表
    def _build_left(self, parent):
        left = tk.Frame(parent, bg=BG, width=300)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        parent.grid_columnconfigure(0, weight=0, minsize=300)
        left.pack_propagate(False)

        card = tk.Frame(left, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        card.pack(fill="both", expand=True)
        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(inner, text="邮箱账号", bg=CARD, fg=TEXT, font=F_MID).pack(anchor="w")

        self.acct_box = tk.Listbox(inner, bg=BG, fg=TEXT, font=F_NORM,
                                   highlightbackground=LINE, highlightthickness=1,
                                   selectbackground=ACC_DK, selectforeground="#ffffff",
                                   activestyle="none", bd=0)
        self.acct_box.pack(fill="both", expand=True, pady=(10, 10))
        self.acct_box.bind("<<ListboxSelect>>", self.on_select)
        self.acct_box.bind("<Double-Button-1>", lambda e: self.fetch_now())

        row = tk.Frame(inner, bg=CARD)
        row.pack(fill="x")
        ttk.Button(row, text="＋ 添加", style="Acc.TButton", command=self.dlg_add).pack(side="left", expand=True, fill="x")
        ttk.Button(row, text="删除", style="Red.TButton", command=self.del_acct).pack(side="left", padx=(8, 0))

        self.acct_hint = tk.Label(inner, text="还没有账号\n点「＋ 添加」开始",
                                  bg=CARD, fg=TEXT_DIM, font=F_SMALL, justify="center")
        self.acct_hint.pack(pady=(14, 0))

    # ---- 右:2FA 卡 + 收件箱
    def _build_right(self, parent):
        right = tk.Frame(parent, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        self._build_totp_card(right)
        self._build_inbox(right)

    def _build_totp_card(self, parent):
        card = tk.Frame(parent, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 14))

        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="x", padx=18, pady=14)
        inner.grid_columnconfigure(1, weight=1)

        # 左:2FA 大码
        left = tk.Frame(inner, bg=CARD)
        left.grid(row=0, column=0, sticky="w")
        tk.Label(left, text="2FA 身份验证器验证码", bg=CARD, fg=TEXT_DIM,
                 font=F_SMALL).pack(anchor="w")
        self.totp_code = tk.Label(left, text="—— —— ——", bg=CODE_BG, fg=CODE_FG,
                                  font=("Consolas", 30, "bold"), padx=20, pady=10)
        self.totp_code.pack(anchor="w", pady=(6, 0))

        # 中:倒计时 + 进度条(可伸缩)
        mid = tk.Frame(inner, bg=CARD)
        mid.grid(row=0, column=1, sticky="ew", padx=(22, 18))
        self.totp_time = tk.Label(mid, text="剩余 -- 秒", bg=CARD, fg=TEXT_DIM, font=F_NORM)
        self.totp_time.pack(anchor="w")
        self.totp_bar = ttk.Progressbar(mid, maximum=30)
        self.totp_bar.pack(fill="x", pady=(8, 0))

        # 右:按钮(固定宽度,不会被挤掉)
        rightb = tk.Frame(inner, bg=CARD, width=126)
        rightb.grid(row=0, column=2, sticky="e")
        rightb.pack_propagate(False)
        ttk.Button(rightb, text="复制验证码", style="Acc.TButton",
                   command=self.copy_totp).pack(fill="x")
        ttk.Button(rightb, text="刷新", style="TButton",
                   command=self.refresh_totp).pack(fill="x", pady=(8, 0))

    def _build_inbox(self, parent):
        card = tk.Frame(parent, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        card.grid(row=1, column=0, sticky="nsew")
        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="both", expand=True, padx=16, pady=14)
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_rowconfigure(2, weight=1)

        head = tk.Frame(inner, bg=CARD)
        head.grid(row=0, column=0, sticky="ew")
        tk.Label(head, text="收件箱", bg=CARD, fg=TEXT, font=F_MID).pack(side="left")
        self.mail_stat = tk.Label(head, text="0 封", bg=CARD, fg=TEXT_DIM, font=F_SMALL)
        self.mail_stat.pack(side="left", padx=(10, 0), pady=(4, 0))
        ttk.Button(head, text="立即收取", style="TButton",
                   command=self.fetch_now).pack(side="right")

        cols = ("subj", "code", "time")
        self.tree = ttk.Treeview(inner, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("subj", text="主题")
        self.tree.heading("code", text="验证码")
        self.tree.heading("time", text="时间")
        # 固定像素列宽在 DPI 缩放下会错位,改用 weight 随窗口自适应
        self.tree.column("subj", width=420, minwidth=180, stretch=True, anchor="w")
        self.tree.column("code", width=130, minwidth=110, stretch=False, anchor="center")
        self.tree.column("time", width=170, minwidth=120, stretch=False, anchor="center")
        self.tree.tag_configure("has", foreground="#fbbf24")
        self.tree.bind("<Double-Button-1>", self.on_mail_dbl)
        self.tree.grid(row=2, column=0, sticky="nsew", pady=(10, 0))

        self.detail = tk.Text(inner, height=7, bg=BG, fg=TEXT, font=F_NORM,
                              wrap="word", highlightbackground=LINE, highlightthickness=1,
                              bd=0, padx=12, pady=10, insertbackground=TEXT)
        self.detail.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self.detail.tag_configure("code", foreground="#fbbf24",
                                  font=("Consolas", 12, "bold"))
        self.detail.configure(state="disabled")

        self.empty_lbl = tk.Label(inner, text="暂无邮件\n点「立即收取」查询，或开启实时监控",
                                  bg=BG, fg=TEXT_DIM, font=F_SMALL, justify="center")
        self.empty_lbl.place(relx=0.5, rely=0.5, anchor="center", in_=self.detail)

        # 滚动条
        sb = ttk.Scrollbar(inner, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.grid(row=2, column=1, sticky="ns", pady=(10, 0))

    def _build_bottom(self):
        self.status = tk.Label(self.root, text="就绪", bg=CARD, fg=TEXT_DIM,
                               font=F_SMALL, anchor="w", padx=18, pady=7)
        self.status.pack(fill="x", side="bottom")
        tk.Frame(self.root, bg=LINE, height=1).pack(fill="x", side="bottom")

        btns = tk.Frame(self.root, bg=CARD)
        btns.pack(fill="x", side="bottom")
        ttk.Button(btns, text="批量导出验证码", command=self.export).pack(side="left", padx=(14, 8), pady=7)
        ttk.Button(btns, text="刷新账号", command=self.reload_accounts).pack(side="left", pady=7)
        tk.Frame(self.root, bg=CARD, height=2).pack(fill="x", side="bottom")

    # ------------------------------------------------------------ 账号
    def _sync_accounts(self):
        self.acct_box.delete(0, "end")
        self.accounts = mp.load_accounts()
        for a in self.accounts:
            self.acct_box.insert("end", a.get("email", ""))
        if self.accounts:
            if self.cur >= len(self.accounts):
                self.cur = 0
            self.acct_box.selection_clear(0, "end")
            self.acct_box.selection_set(self.cur)
            self.acct_box.see(self.cur)
            self.acct_hint.pack_forget()
            self.clear_inbox()
        else:
            self.acct_hint.pack(pady=(14, 0))
            self.totp_code.configure(text="—— —— ——")
            self.totp_time.configure(text="剩余 -- 秒")
            self.totp_bar["value"] = 0

    def reload_accounts(self):
        self._sync_accounts()
        self.refresh_totp()
        self.set_status("账号已刷新")

    def on_select(self, _):
        sel = self.acct_box.curselection()
        if sel:
            self.cur = sel[0]
            self.seen = set()          # 切号后重新判定"新邮件"
            self.refresh_totp()
            self.clear_inbox()
            self.fetch_now()

    def cur_acct(self):
        if not self.accounts or self.cur >= len(self.accounts):
            return None
        return self.accounts[self.cur]

    # ------------------------------------------------------------ 2FA
    def refresh_totp(self):
        a = self.cur_acct()
        if not a:
            return
        code, left = mp.totp(a.get("secret", ""))
        if code:
            pretty = f"{code[:3]} {code[3:]}"
            self.totp_code.configure(text=pretty)
            self.remain = left
            self.totp_bar["maximum"] = 30
            self.totp_bar["value"] = left
            self.totp_time.configure(text=f"剩余 {left} 秒后刷新")
        else:
            self.totp_code.configure(text="未设置 2FA")
            self.totp_time.configure(text="添加账号时带上秘钥即可启用")
            self.totp_bar["value"] = 0

    def copy_totp(self):
        a = self.cur_acct()
        if not a:
            return
        code, _ = mp.totp(a.get("secret", ""))
        if code:
            self.root.clipboard_clear()
            self.root.clipboard_append(code)
            self.set_status(f"已复制 2FA 验证码: {code}")

    def _tick(self):
        """每秒刷新倒计时和进度条。"""
        a = self.cur_acct()
        if a and a.get("secret"):
            code, left = mp.totp(a.get("secret", ""))
            self.remain = left
            self.totp_bar["value"] = left
            self.totp_time.configure(text=f"剩余 {left} 秒后刷新")
            bar = self.totp_bar
            bar.configure(style="TProgressbar")
            if left <= 5:
                bar["value"] = 30 - left + 1
        self.root.after(1000, self._tick)

    # ------------------------------------------------------------ 收信
    def clear_inbox(self):
        self.tree.delete(*self.tree.get_children())
        self.mail_stat.configure(text="0 封")
        self._set_detail("")
        self.empty_lbl.lift()
        self.empty_lbl.configure(text="暂无邮件\n点「立即收取」查询，或开启实时监控")

    def _set_detail(self, text, code=None):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        if code:
            self.detail.insert("end", "验证码: ", "code")
            self.detail.insert("end", f"{code}\n\n", "code")
        self.detail.insert("end", text)
        self.detail.configure(state="disabled")

    def fetch_now(self, silent=False):
        a = self.cur_acct()
        if not a:
            if not silent:
                messagebox.showinfo("提示", "请先添加一个邮箱账号")
            return
        if not silent:
            self.set_status("正在收取邮件…")
        self._bg_fetch(a.get("email"), a.get("api", ""))

    def _drain(self):
        """后台线程结果回主线程。"""
        try:
            while True:
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "fetch":
                    # (kind, email, data)
                    _, email, data = msg
                    self._render(email, data)
                elif kind == "err":
                    self.set_status(msg[1])
                    if not self.watching:
                        messagebox.showerror("出错了", msg[1])
        except queue.Empty:
            pass
        self.root.after(80, self._drain)

    def _render(self, email, data):
        if data is None:
            self.set_status("收取失败")
            return
        mails = mp.norm_mail(data)
        # 切号了就丢弃旧结果
        a = self.cur_acct()
        if not a or a.get("email") != email:
            return

        self.tree.delete(*self.tree.get_children())
        newest = False
        for i, m in enumerate(mails):
            d = mp.mail_fields(m)
            mid = mp.mail_id(m, i)
            tag = "has" if d.get("code") else ""
            self.tree.insert("", "end", values=(d["subject"] or "(无主题)",
                                                 d.get("code") or "—", d.get("time") or ""),
                             tags=(tag,))
            if mid not in self.seen and i == 0:
                newest = True
            self.seen.add(mid)

        self.mail_stat.configure(text=f"{len(mails)} 封")
        if mails:
            self.empty_lbl.lower()
            self.tree.selection_set(0)
            self._show_detail(mails[0])
        else:
            self.empty_lbl.lift()

        if newest and self.watching:
            d0 = mp.mail_fields(mails[0])
            code = d0.get("code")
            self.set_status(f"收到新邮件: {d0['subject'][:40]}" + (f"  验证码 {code}" if code else ""))
            if code:
                self.root.bell()
        elif not self.watching:
            self.set_status(f"收取完成，共 {len(mails)} 封邮件")

    def _show_detail(self, raw):
        d = mp.mail_fields(raw)
        body = " ".join((d["body"] or "").split())
        self._set_detail(f"【{d['subject'] or '(无主题)'}】\n{d['time']}\n\n{body}", d.get("code"))
        if d.get("code"):
            self.root.clipboard_clear()
            self.root.clipboard_append(d["code"])

    def on_mail_dbl(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        if vals and vals[1] and vals[1] != "—":
            self.root.clipboard_clear()
            self.root.clipboard_append(vals[1])
            self.set_status(f"已复制验证码: {vals[1]}")

    # ------------------------------------------------------------ 监控
    def toggle_watch(self):
        self.watching = not self.watching
        if self.watching:
            self.watch_btn.configure(text="■  停止监控", style="Red.TButton")
            self.set_status("实时监控已开启，新邮件会自动刷新")
            self.root.after(200, self._watch_tick)
        else:
            self.watch_btn.configure(text="▶  实时监控", style="Green.TButton")
            self.set_status("实时监控已停止")

    def _watch_tick(self):
        if not self.watching:
            return
        a = self.cur_acct()
        if a:
            self._bg_fetch(a.get("email"), a.get("api", ""))
        self.root.after(5000, self._watch_tick)

    def _bg_fetch(self, email, api):
        """后台线程请求，避免界面卡住。"""
        def work():
            try:
                self.q.put(("fetch", email, mp.fetch(email, api)))
            except Exception as e:
                if self.watching:
                    self.q.put(("err", f"{email} — {e}",))
        threading.Thread(target=work, daemon=True).start()

    # ------------------------------------------------------------ 对话框
    def dlg_add(self):
        win = tk.Toplevel(self.root)
        win.title("添加邮箱账号")
        win.configure(bg=BG)
        win.transient(self.root)
        win.resizable(False, False)
        w, h = 480, 350
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        f = tk.Frame(win, bg=BG)
        f.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(f, text="添加邮箱账号", bg=BG, fg=TEXT, font=F_TITLE).pack(anchor="w")
        tk.Label(f, text="支持直接粘贴: 邮箱----密码----2FA秘钥", bg=BG, fg=TEXT_DIM,
                 font=F_SMALL).pack(anchor="w", pady=(4, 16))

        e_email = tk.StringVar()
        e_pass = tk.StringVar()
        e_key = tk.StringVar()
        e_api = tk.StringVar()

        def labeled(text, var, placeholder, show=None):
            tk.Label(f, text=text, bg=BG, fg=TEXT_DIM, font=F_SMALL).pack(anchor="w", pady=(8, 3))
            ent = ttk.Entry(f, textvariable=var, font=F_NORM)
            ent.pack(fill="x")
            ent.insert(0, "")
            if show:
                ent.configure(show=show)
            return ent

        e1 = labeled("邮箱地址", e_email, "")
        labeled("登录密码", e_pass, "", show="*")
        labeled("2FA 秘钥 (可选)", e_key, "")
        labeled("收信接口 (可选,留空自动探测)", e_api, "")

        def split_paste(e):
            txt = e.widget.get("1.0", "end").strip()
            if "----" in txt:
                parts = [p.strip() for p in txt.split("----")]
                e_email.set(parts[0] if parts else "")
                e_pass.set(parts[1] if len(parts) > 1 else "")
                e_key.set(parts[2] if len(parts) > 2 else "")

        e1.bind("<FocusOut>", split_paste)
        e1.focus_set()

        tip = tk.Label(f, text="", bg=BG, fg=GREEN, font=F_SMALL, anchor="w")
        tip.pack(anchor="w", pady=(10, 0))

        def do_add():
            em, pw, ky = e_email.get().strip(), e_pass.get().strip(), e_key.get().strip()
            if not em or "@" not in em:
                tip.configure(text="✗ 邮箱格式不对,应为 user@example.com", fg=RED)
                return
            if not pw:
                tip.configure(text="✗ 密码不能为空", fg=RED)
                return
            accts = mp.load_accounts()
            accts = [a for a in accts if a.get("email", "").lower() != em.lower()]
            accts.append({"email": em, "password": pw, "secret": ky,
                          "api": e_api.get().strip(), "added": time.strftime("%Y-%m-%d %H:%M:%S")})
            mp.save_accounts(accts)
            win.destroy()
            self._sync_accounts()
            self.cur = len(self.accounts) - 1
            self.acct_box.selection_clear(0, "end")
            self.acct_box.selection_set(self.cur)
            self.refresh_totp()
            self.set_status(f"已添加账号: {em}")
            if ky:
                c, _ = mp.totp(ky)
                self.set_status(f"已添加 {em}   2FA 秘钥有效: {c}")

        btns = tk.Frame(f, bg=BG)
        btns.pack(fill="x", side="bottom", pady=(16, 0))
        ttk.Button(btns, text="取消", style="TButton", command=win.destroy).pack(side="right")
        ttk.Button(btns, text="确认添加", style="Acc.TButton", command=do_add).pack(side="right", padx=(0, 8))
        win.bind("<Return>", lambda e: do_add())

    def del_acct(self):
        a = self.cur_acct()
        if not a:
            return
        if not messagebox.askyesno("确认删除", f"确定删除账号:\n{a['email']} ?"):
            return
        accts = [x for x in mp.load_accounts()
                 if x.get("email", "").lower() != a["email"].lower()]
        mp.save_accounts(accts)
        self.cur = 0
        self._sync_accounts()
        self.refresh_totp()
        self.set_status("账号已删除")

    def export(self):
        if not self.accounts:
            messagebox.showinfo("提示", "还没有账号")
            return
        path = filedialog.asksaveasfilename(
            title="导出验证码",
            defaultextension=".csv",
            initialfile=f"验证码_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            filetypes=[("CSV 文件", "*.csv"), ("JSON 文件", "*.json")])
        if not path:
            return
        rows = []
        for a in self.accounts:
            c, _ = mp.totp(a.get("secret", ""))
            try:
                mails = mp.norm_mail(mp.fetch(a["email"], a.get("api")))
                latest = mp.mail_fields(mails[0]) if mails else {}
                code, subj = latest.get("code") or "", latest.get("subject") or ""
                n = len(mails)
            except Exception:
                code, subj, n = "", "", 0
            rows.append({"email": a["email"], "password": a.get("password", ""),
                         "2FA验证码": c, "邮件验证码": code,
                         "主题": subj, "邮件数": n})
            time.sleep(0.6)
        try:
            if path.endswith(".json"):
                import json
                with open(path, "w", encoding="utf-8") as fp:
                    json.dump(rows, fp, ensure_ascii=False, indent=2)
            else:
                import csv
                with open(path, "w", encoding="utf-8-sig", newline="") as fp:
                    w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
                    w.writeheader()
                    w.writerows(rows)
            self.set_status(f"已导出 {len(rows)} 个账号到 {os.path.basename(path)}")
            messagebox.showinfo("导出成功", f"已导出 {len(rows)} 个账号\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    # ------------------------------------------------------------ 杂项
    def set_status(self, msg):
        self.status.configure(text=f"  {msg}")

    def _close(self):
        self.watching = False
        try:
            mp.save_accounts(mp.load_accounts())
        except Exception:
            pass
        self.root.destroy()


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()