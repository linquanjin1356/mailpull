#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MailPull Web 构建脚本
  1. 用 Tailwind CLI 扫描 index.src.html + app.js，编译出 CSS
  2. 把 CSS 内联进页面，产出可直接托管的 index.html（离线、零外链）

用法: python build.py
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "index.src.html"
OUT = HERE / "index.html"
CSS_OUT = HERE / "tw.out.css"
CLI = HERE.parent / "marketing-sections" / "node_modules" / ".bin" / "tailwindcss"


def main():
    if not SRC.exists():
        sys.exit(f"缺少源文件: {SRC}")
    if not CLI.exists():
        sys.exit(f"缺少 Tailwind CLI: {CLI}\n(需要先执行 npm install)")

    print("[1/2] 编译 Tailwind CSS ...")
    r = subprocess.run(
        ["sh", str(CLI), "-c", "tw.config.js", "-i", "tw.input.css",
         "-o", "tw.out.css", "--minify"],
        cwd=HERE, capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        sys.exit("CSS 编译失败")
    css = CSS_OUT.read_text(encoding="utf-8")
    print(f"      {len(css) / 1024:.1f} KB")

    print("[2/2] 内联到页面 ...")
    html = SRC.read_text(encoding="utf-8")
    if "<!--TAILWIND_CSS-->" not in html:
        sys.exit("源文件缺少 <!--TAILWIND_CSS--> 占位符")
    html = html.replace(
        "<!--TAILWIND_CSS-->",
        "<style>\n/* Tailwind 编译产物（离线内联） */\n" + css + "\n</style>",
    )
    OUT.write_text(html, encoding="utf-8")

    # 自检
    import re
    ext = re.findall(r'(?:src|href)="https?://[^"]+"', html)
    print(f"      输出 {OUT.name}: {len(html.encode('utf-8')) / 1024:.1f} KB")
    print(f"      外部依赖: {ext if ext else '无（完全离线）'}")


if __name__ == "__main__":
    main()