#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把编译好的 Tailwind CSS 内联进 preview.html，生成完全离线可打开的版本。"""
import re
from pathlib import Path

root = Path(__file__).parent
html_path = root / "preview.html"
css_path = root / "marketing-sections" / "preview.compiled.css"

html = html_path.read_text(encoding="utf-8")
css = css_path.read_text(encoding="utf-8")

# 1) 删掉 CDN 脚本
html = html.replace('<script src="https://cdn.tailwindcss.com"></script>\n', "")

# 2) 删掉 tailwind.config 赋值行（离线版不需要运行时配置）
html = re.sub(r"\n\s*tailwind\.config = \{[^}]*\};\n", "\n", html)

# 3) 把 <style> ... </style> 整块替换为编译后的 CSS
#    编译产物已包含 .text-balance 与 reduced-motion，无需重复
new_style = f"<style>\n/* Tailwind 编译产物（离线内联，无需联网） */\n{css}\n</style>"

html, n = re.subn(r"<style>.*?</style>", new_style, html, count=1, flags=re.S)
assert n == 1, "未找到 <style> 块"

# 4) 标题注明离线
html = html.replace("<title>营销区块预览 · Nucleus</title>",
                    "<title>营销区块预览 · Nucleus（离线版）</title>")

html_path.write_text(html, encoding="utf-8")
print(f"已内联 CSS: {len(css)/1024:.1f} KB")
print(f"输出: {html_path}")
print(f"文件大小: {html_path.stat().st_size/1024:.1f} KB")

# 自检：不应再有任何外链
rem = re.findall(r'(?:src|href)="https?://[^"]+"', html)
print("外部依赖:", rem if rem else "无（完全离线）")
