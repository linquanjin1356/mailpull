import type { ReactNode } from "react";

/**
 * LogoCloud — 品牌标识区
 *
 * 规格（严格对齐需求）:
 *   grid : grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-8 items-center
 *   标识  : 默认灰度 (grayscale)，悬停恢复颜色 (hover:grayscale-0)
 *
 * 对比度: 品牌名用 zinc-500 / dark:zinc-400，在两种主题下均 >= 4.5:1
 *   浅色 zinc-500(#71717a) on white(#fff)  = 4.83:1  ✅
 *   暗色 zinc-400(#a1a1aa) on zinc-950      = 8.4:1   ✅
 */

type Logo = {
  name: string;
  /** 品牌主色，用于 hover 时恢复彩色 */
  tint: string;
  glyph: ReactNode;
};

const LOGOS: Logo[] = [
  {
    name: "Nimbus",
    tint: "#38bdf8",
    glyph: (
      <>
        <path d="M6 30c0-5 4-9 9-9 2-6 8-9 13-6 4 2 6 7 5 12 4 0 7 3 7 7H6z" />
      </>
    ),
  },
  {
    name: "Vertex",
    tint: "#a78bfa",
    glyph: (
      <>
        <path d="M22 6 38 34H6z" />
        <path d="M22 17 31 34H13z" className="opacity-40" />
      </>
    ),
  },
  {
    name: "Orbit",
    tint: "#f472b6",
    glyph: (
      <>
        <circle cx="22" cy="22" r="9" />
        <ellipse cx="22" cy="22" rx="17" ry="7" className="opacity-40" />
      </>
    ),
  },
  {
    name: "Forge",
    tint: "#fb923c",
    glyph: (
      <>
        <rect x="8" y="8" width="13" height="13" rx="3" />
        <rect x="23" y="23" width="13" height="13" rx="3" className="opacity-40" />
        <path d="M21 8h2M8 21v2" strokeWidth="0" />
      </>
    ),
  },
  {
    name: "Atlas",
    tint: "#34d399",
    glyph: (
      <>
        <circle cx="22" cy="22" r="15" className="opacity-30" />
        <path d="M7 22h30M22 7c5 5 5 25 0 30M22 7c-5 5-5 25 0 30" />
      </>
    ),
  },
  {
    name: "Lumen",
    tint: "#facc15",
    glyph: (
      <>
        <path d="M22 8v8M22 28v8M8 22h8M28 22h8" />
        <circle cx="22" cy="22" r="6" />
      </>
    ),
  },
];

export default function LogoCloud() {
  return (
    <section className="border-y border-zinc-200 bg-zinc-50/50 py-16 dark:border-zinc-800 dark:bg-zinc-900/30">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <p className="text-center text-xs font-semibold uppercase tracking-widest text-zinc-500 dark:text-zinc-400">
          已有 4,000+ 团队在生产环境使用
        </p>

        <div className="mt-12 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-8 items-center">
          {LOGOS.map((logo) => (
            <div
              key={logo.name}
              className="group flex items-center justify-center gap-2.5 transition-opacity duration-300"
            >
              {/* 图标默认灰度，hover 恢复品牌色 */}
              <svg
                viewBox="0 0 44 44"
                className="h-8 w-8 shrink-0 grayscale transition-all duration-300 group-hover:grayscale-0"
                fill={logo.tint}
                stroke={logo.tint}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                {logo.glyph}
              </svg>

              {/* 品牌名：颜色也跟随主题，保证 4.5:1 */}
              <span className="text-sm font-semibold text-zinc-500 transition-colors duration-300 group-hover:text-zinc-900 dark:text-zinc-400 dark:group-hover:text-white">
                {logo.name}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}