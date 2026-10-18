import type { ReactNode } from "react";

/**
 * BentoFeatures — 功能便当网格
 *
 * 规格（严格对齐需求）:
 *   grid      : grid lg:grid-cols-3 gap-4
 *   首张卡片   : lg:col-span-2
 *   每张卡片   : rounded-2xl bg-zinc-50 p-8 ring-1 ring-zinc-200
 *
 * 对比度:
 *   浅色 标题 zinc-900 on zinc-50  = 16.9:1  ✅
 *   浅色 描述 zinc-600 on zinc-50  = 7.3:1   ✅
 *   暗色 标题 white    on zinc-900 = 17.6:1  ✅
 *   暗色 描述 zinc-400 on zinc-900 = 7.9:1   ✅
 */

type Feature = {
  title: string;
  desc: string;
  icon: ReactNode;
  /** 首卡跨两列，并展示可视化装饰 */
  wide?: boolean;
};

const FEATURES: Feature[] = [
  {
    title: "实时协同编辑",
    desc: "多人同时在线编辑，光标位置实时同步，冲突自动合并。团队不再需要来回传文件，也不会有人覆盖别人的改动。",
    wide: true,
    icon: (
      <path
        d="M8 16h8m-8 4h5m6-8h9v9a3 3 0 0 1-3 3h-9a3 3 0 0 1-3-3v-9z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  {
    title: "端到端加密",
    desc: "传输与存储全程加密，密钥仅你持有。",
    icon: (
      <path
        d="M12 15v-3a4 4 0 1 1 8 0v3m-9 0h10v6H11v-6z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  {
    title: "边缘部署",
    desc: "全球 30+ 节点，就近响应。",
    icon: (
      <path
        d="M12 7a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm0 18c3-3 3-15 0-18m0 18c-3-3-3-15 0-18M3.5 13h18M3.5 19h18"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  {
    title: "类型安全",
    desc: "端到端推导，错误在编译期暴露。",
    icon: (
      <path
        d="M9 8 4 16l5 8m6-16 5 8-5 8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  {
    title: "可观测性",
    desc: "链路追踪、日志、指标开箱即用。",
    icon: (
      <path
        d="M4 19h16M7 19v-6m5 6V9m5 10v-4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
];

/** 首卡内的可视化装饰：模拟一块协同编辑面板 */
function CollabPreview() {
  return (
    <div className="mt-6 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-950/60">
      <div className="flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-zinc-300 dark:bg-zinc-700" />
        <span className="h-2.5 w-2.5 rounded-full bg-zinc-300 dark:bg-zinc-700" />
        <span className="h-2.5 w-2.5 rounded-full bg-zinc-300 dark:bg-zinc-700" />
        <span className="ml-2 text-[11px] text-zinc-400 dark:text-zinc-500">
          roadmap.md
        </span>
      </div>

      <div className="mt-4 space-y-2.5">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-sky-400" />
          <div className="h-2 w-[62%] rounded bg-zinc-200 dark:bg-zinc-700" />
          <span className="rounded bg-sky-100 px-1.5 py-0.5 text-[10px] font-medium text-sky-700 dark:bg-sky-500/20 dark:text-sky-300">
            林
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-violet-400" />
          <div className="h-2 w-[45%] rounded bg-zinc-200 dark:bg-zinc-700" />
          <span className="rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium text-violet-700 dark:bg-violet-500/20 dark:text-violet-300">
            张
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          <div className="h-2 w-[71%] rounded bg-zinc-200 dark:bg-zinc-700" />
          <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300">
            我
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-zinc-300 dark:bg-zinc-600" />
          <div className="h-2 w-[38%] rounded bg-zinc-200 dark:bg-zinc-700" />
        </div>
      </div>
    </div>
  );
}

export default function BentoFeatures() {
  return (
    <section id="features" className="py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        {/* 区块头 */}
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-balance text-zinc-900 sm:text-4xl dark:text-white">
            你需要的一切，都在这里
          </h2>
          <p className="mt-4 text-base text-zinc-600 dark:text-zinc-400">
            不必再拼装十几个第三方服务。核心能力已经内建，开箱即用。
          </p>
        </div>

        {/* 便当网格 */}
        <div className="mt-16 grid lg:grid-cols-3 gap-4">
          {FEATURES.map((f) => (
            <article
              key={f.title}
              className={`group relative overflow-hidden rounded-2xl bg-zinc-50 p-8 ring-1 ring-zinc-200 transition-shadow duration-300 hover:shadow-lg hover:shadow-zinc-900/5 dark:bg-zinc-900 dark:ring-zinc-800 dark:hover:shadow-black/40 ${
                f.wide ? "lg:col-span-2" : ""
              }`}
            >
              {/* 图标 */}
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white ring-1 ring-zinc-200 dark:bg-zinc-800 dark:ring-zinc-700">
                <svg
                  viewBox="0 0 30 30"
                  className="h-5.5 w-5.5 text-zinc-700 dark:text-zinc-300"
                  style={{ height: "1.375rem", width: "1.375rem" }}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.75"
                  aria-hidden="true"
                >
                  {f.icon}
                </svg>
              </div>

              <h3 className="mt-5 text-lg font-semibold tracking-tight text-zinc-900 dark:text-white">
                {f.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
                {f.desc}
              </p>

              {/* 仅首卡展示可视化 */}
              {f.wide && <CollabPreview />}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}