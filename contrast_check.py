#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WCAG 对比度校验 —— 验证三个区块的标题/正文在明暗主题下均 >= 4.5:1"""

def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def srgb(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

def lum(rgb):
    r, g, b = (srgb(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def ratio(fg, bg):
    l1, l2 = lum(hex2rgb(fg)), lum(hex2rgb(bg))
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)

# Tailwind zinc 色板实际值
C = {
    "white":    "#ffffff",
    "zinc-50":  "#fafafa",
    "zinc-100": "#f4f4f5",
    "zinc-200": "#e4e4e7",
    "zinc-300": "#d4d4d8",
    "zinc-400": "#a1a1aa",
    "zinc-500": "#71717a",
    "zinc-600": "#52525b",
    "zinc-700": "#3f3f46",
    "zinc-800": "#27272a",
    "zinc-900": "#18181b",
    "zinc-950": "#09090b",
}

TAG = {
    "white": "zinc-950", "zinc-50": "zinc-950",
}

CHECKS = [
    # (说明, 前景, 背景, 用途)
    ("Hero 标题 (浅色)",      "zinc-900", "white",   "大标题"),
    ("Hero 标题 (暗色)",      "white",    "zinc-950","大标题"),
    ("Hero 说明 (浅色)",      "zinc-600", "white",   "正文"),
    ("Hero 说明 (暗色)",      "zinc-400", "zinc-950","正文"),
    ("Hero 信任行 (浅色)",    "zinc-500", "white",   "小字"),
    ("Hero 信任行 (暗色)",    "zinc-400", "zinc-950","小字"),
    ("Hero 次按钮文字(浅)",   "zinc-700", "white",   "按钮"),
    ("Hero 次按钮文字(暗)",   "zinc-300", "zinc-950","按钮"),
    ("Hero 主按钮 (浅色)",    "white",    "zinc-900","按钮"),
    ("Hero 主按钮 (暗色)",    "zinc-900", "white",   "按钮"),

    ("Logo 品牌名 (浅色)",    "zinc-500", "white",   "标识"),
    ("Logo 品牌名 (暗色)",    "zinc-400", "zinc-900","标识"),
    ("Logo 小标题 (浅色)",    "zinc-500", "zinc-50", "说明"),
    ("Logo 小标题 (暗色)",    "zinc-400", "zinc-900","说明"),

    ("Bento 标题 (浅色)",     "zinc-900", "zinc-50", "卡片标题"),
    ("Bento 标题 (暗色)",     "white",    "zinc-900","卡片标题"),
    ("Bento 描述 (浅色)",     "zinc-600", "zinc-50", "卡片正文"),
    ("Bento 描述 (暗色)",     "zinc-400", "zinc-900","卡片正文"),
    ("Bento 区块标题(浅色)",  "zinc-900", "white",   "区块标题"),
    ("Bento 区块标题(暗色)",  "white",    "zinc-950","区块标题"),
    ("Bento 区块说明(浅色)",  "zinc-600", "white",   "区块正文"),
    ("Bento 区块说明(暗色)",  "zinc-400", "zinc-950","区块正文"),
]

AA_NORMAL = 4.5
AA_LARGE = 3.0

print(f"{'检查项':<24}{'前景':<10}{'背景':<10}{'对比度':>8}  {'判定'}")
print("-" * 74)
fails = []
for name, fg, bg, kind in CHECKS:
    r = ratio(C[fg], C[bg])
    # 大标题(>=24px粗体)按 AA Large 3.0; 但需求要求 >=4.5, 统一按 4.5 更严
    need = AA_NORMAL
    ok = r >= need
    if not ok:
        fails.append((name, r))
    mark = "PASS" if ok else "FAIL"
    print(f"{name:<24}{fg:<10}{bg:<10}{r:>8.2f}  {mark}  (需 {need})")

print("-" * 74)
if fails:
    print(f"\n未通过 {len(fails)} 项:")
    for n, r in fails:
        print(f"  - {n}: {r:.2f}")
    raise SystemExit(1)
print(f"\n全部 {len(CHECKS)} 项 >= 4.5:1，符合 WCAG AA")
