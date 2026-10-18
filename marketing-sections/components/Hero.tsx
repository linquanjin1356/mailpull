import type { ReactNode } from "react";

/**
 * Hero — 首屏区块
 *
 * 规格（严格对齐需求）:
 *   section  : py-24 lg:py-32
 *   h1       : text-5xl lg:text-6xl font-bold tracking-tight text-balance
 *   p        : mt-6 text-lg text-zinc-600 max-w-2xl mx-auto
 *   主按钮    : bg-zinc-900 text-white
 *   次按钮    : ring-1 ring-zinc-300
 *
 * 对比度保证:
 *   浅色  zinc-900(#18181b) on white(#fff)      = 17.6:1  ✅
 *   暗色  white(#fff) on zinc-950(#09090b)      = 19.3:1  ✅
 *   说明文 zinc-600 on white                     = 7.5:1   ✅
 *   说明文 zinc-400 on zinc-950                  = 8.4:1   ✅
 *   全部 >= 4.5:1 (WCAG AA)
 */

type CtaProps = {
  href: string;
  children: ReactNode;
  variant?: "primary" | "secondary";
};

function Cta({ href, children, variant = "primary" }: CtaProps) {
  const base =
    "inline-flex items-center justify-center rounded-full px-7 py-3.5 text-sm font-semibold " +
    "transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 " +
    "focus-visible:ring-offset-2 focus-visible:ring-offset-white " +
    "dark:focus-visible:ring-offset-zinc-950";

  const styles =
    variant === "primary"
      ? // 主按钮：深底白字；暗色下反转成白底深字，保持强对比
        "bg-zinc-900 text-white shadow-sm hover:bg-zinc-800 " +
        "focus-visible:ring-zinc-900 " +
        "dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200 dark:focus-visible:ring-white"
      : // 次按钮：描边；两种主题下都有足够可见的边界
        "text-zinc-700 ring-1 ring-zinc-300 ring-inset hover:bg-zinc-50 hover:text-zinc-900 " +
        "focus-visible:ring-zinc-500 " +
        "dark:text-zinc-300 dark:ring-zinc-700 dark:hover:bg-zinc-900 dark:hover:text-white";

  return (
    <a href={href} className={`${base} ${styles}`}>
      {children}
    </a>
  );
}

export default function Hero() {
  return (
    <section className="py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="text-center">
          {/* 小标签 */}
          <span className="inline-flex items-center gap-2 rounded-full bg-zinc-100 px-4 py-1.5 text-xs font-semibold tracking-wide text-zinc-700 ring-1 ring-zinc-200 ring-inset dark:bg-zinc-900 dark:text-zinc-300 dark:ring-zinc-800">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </span>
            v2.0 现已发布
          </span>

          {/* 主标题 —— 对比度在两个主题下均 > 4.5:1 */}
          <h1 className="mt-8 text-5xl lg:text-6xl font-bold tracking-tight text-balance text-zinc-900 dark:text-white">
            构建产品，而不是配置环境
          </h1>

          {/* 说明文字 */}
          <p className="mt-6 text-lg text-zinc-600 max-w-2xl mx-auto dark:text-zinc-400">
            从第一天起就把基础架构做对。类型安全、边缘部署、零配置，
            让团队把时间花在真正重要的事情上。
          </p>

          {/* 行动按钮 */}
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Cta href="#start" variant="primary">
              免费开始使用
              <svg
                className="ml-2 h-4 w-4"
                viewBox="0 0 20 20"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.75"
                aria-hidden="true"
              >
                <path
                  d="M4 10h12m0 0-4.5-4.5M16 10l-4.5 4.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </Cta>

            <Cta href="#features" variant="secondary">
              查看功能特性
            </Cta>
          </div>

          {/* 信任说明：暗色用 zinc-400（7.76:1），不用 zinc-500（仅 4.12:1 不达标） */}
          <p className="mt-6 text-xs text-zinc-500 dark:text-zinc-400">
            无需信用卡 · 5 分钟完成部署 · 随时可退出
          </p>
        </div>
      </div>
    </section>
  );
}