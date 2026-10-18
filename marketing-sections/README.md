# 营销页面区块 · Next.js + Tailwind CSS

三个可直接复用的营销区块，支持亮/暗双主题，标题对比度全部 ≥ 4.5:1 (WCAG AA)。

## 快速开始

```bash
npm install
npm run dev     # 打开 http://localhost:3000
```

## 直接看效果（不用装依赖）

打开根目录的 **`preview.html`** —— 单文件，双击即开，效果与 Next.js 版本一致。

---

## 三个区块

### ① Hero 首屏 — `components/Hero.tsx`

```tsx
import Hero from "@/components/Hero";

<Hero />
```

| 元素 | 类名 |
|---|---|
| 容器 | `py-24 lg:py-32` |
| 标题 | `text-5xl lg:text-6xl font-bold tracking-tight text-balance` |
| 说明 | `mt-6 text-lg text-zinc-600 max-w-2xl mx-auto` |
| 主按钮 | `bg-zinc-900 text-white` |
| 次按钮 | `ring-1 ring-zinc-300` |

暗色变体：
- 标题 `dark:text-white`
- 说明 `dark:text-zinc-400`
- 主按钮反转为 `dark:bg-white dark:text-zinc-900`（暗底白底互换，保持强对比）
- 次按钮 `dark:ring-zinc-700 dark:text-zinc-300`

### ② 品牌标识区 — `components/LogoCloud.tsx`

```tsx
import LogoCloud from "@/components/LogoCloud";

<LogoCloud />
```

| 元素 | 类名 |
|---|---|
| 网格 | `grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-8 items-center` |
| 标识 | `grayscale`（默认灰度）→ `group-hover:grayscale-0`（悬停恢复彩色）|

用 `group` + `group-hover` 让图标和文字联动变色，鼠标移到任意一个 logo 上只高亮它自己。

### ③ 功能便当网格 — `components/BentoFeatures.tsx`

```tsx
import BentoFeatures from "@/components/BentoFeatures";

<BentoFeatures />
```

| 元素 | 类名 |
|---|---|
| 网格 | `grid lg:grid-cols-3 gap-4` |
| 首张卡片 | 额外加 `lg:col-span-2` |
| 每张卡片 | `rounded-2xl bg-zinc-50 p-8 ring-1 ring-zinc-200` |

首卡跨两列，内部嵌了一块「协同编辑」可视化装饰（`CollabPreview`），让便当布局有主次层次。
暗色卡片用 `dark:bg-zinc-900 dark:ring-zinc-800`。

---

## 主题实现方式

`tailwind.config.ts` 里设 `darkMode: "class"`，由 `<html class="dark">` 控制。

`app/layout.tsx` 里有一段内联脚本，在 HTML 解析前读取 `localStorage` / 系统偏好并加 `dark` 类，
**避免暗色模式闪白（FOUC）**。

`components/ThemeToggle.tsx` 是切换按钮，右下角导航里可直接点。

---

## 对比度实测结果

用 `contrast_check.py` 按 WCAG 公式逐一验算（相对亮度 + (L1+0.05)/(L2+0.05)）：

| 场景 | 前景 | 背景 | 对比度 |
|---|---|---|---|
| Hero 标题 亮 | `zinc-900` | `white` | **17.72** |
| Hero 标题 暗 | `white` | `zinc-950` | **19.90** |
| Hero 说明 亮 | `zinc-600` | `white` | **7.73** |
| Hero 说明 暗 | `zinc-400` | `zinc-950` | **7.76** |
| Bento 卡片标题 亮 | `zinc-900` | `zinc-50` | **16.97** |
| Bento 卡片标题 暗 | `white` | `zinc-900` | **17.72** |
| Bento 卡片正文 亮 | `zinc-600` | `zinc-50` | **7.41** |
| Bento 卡片正文 暗 | `zinc-400` | `zinc-900` | **6.91** |

22 项检查全部 ≥ 4.5:1。

> 开发中修过一处：Hero 底部信任行原本写 `dark:text-zinc-500`，实测仅 **4.12:1** 不达标，
> 已改为 `dark:text-zinc-400`（7.76:1）。

---

## 目录结构

```
marketing-sections/
├── app/
│   ├── layout.tsx          # 根布局、顶部导航、页脚、主题恢复脚本
│   ├── page.tsx            # 三个区块的组合示例
│   └── globals.css         # Tailwind 指令 + text-balance 兜底
├── components/
│   ├── Hero.tsx            # ① 首屏
│   ├── LogoCloud.tsx       # ② 品牌标识区
│   ├── BentoFeatures.tsx   # ③ 功能便当网格
│   ├── ThemeToggle.tsx     # 主题切换按钮
│   └── index.ts            # 统一导出
├── tailwind.config.ts
└── package.json
```

## 单独取用

三个组件都**不依赖彼此**，也没有外部图标库（图标全部是内联 SVG）。
把单个 `.tsx` 文件拷进你的项目，确保 `tailwind.config` 的 `content` 覆盖到它即可。

组件内的文案、图标、卡片数量都是数组驱动的，改 `FEATURES` / `LOGOS` 数组就能增删条目。
