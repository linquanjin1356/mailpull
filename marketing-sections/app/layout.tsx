import type { Metadata } from "next";
import "./globals.css";
import ThemeToggle from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: "构建产品，而不是配置环境",
  description:
    "从第一天起就把基础架构做对。类型安全、边缘部署、零配置，让团队把时间花在真正重要的事情上。",
};

/**
 * 首屏恢复主题：在 HTML 解析前同步执行，避免暗色模式闪白。
 * 优先级：localStorage > 系统偏好
 */
const themeScript = `
(function() {
  try {
    var stored = localStorage.getItem('theme');
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (stored === 'dark' || (!stored && prefersDark)) {
      document.documentElement.classList.add('dark');
    }
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-screen bg-white text-zinc-900 antialiased dark:bg-zinc-950 dark:text-zinc-100">
        {/* 顶部导航 */}
        <header className="sticky top-0 z-50 border-b border-zinc-200/80 bg-white/80 backdrop-blur-md dark:border-zinc-800/80 dark:bg-zinc-950/80">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-8">
            <a href="#" className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-900 dark:bg-white">
                <svg viewBox="0 0 24 24" className="h-4 w-4 text-white dark:text-zinc-900" fill="currentColor" aria-hidden="true">
                  <path d="M4 7.5 12 3l8 4.5v9L12 21l-8-4.5v-9Zm8-2.2L6.4 8.2 12 11.4l5.6-3.2L12 5.3ZM6 9.8v6l5 2.8v-6L6 9.8Zm7 8.8 5-2.8v-6l-5 2.8v6Z" />
                </svg>
              </span>
              <span className="text-sm font-bold tracking-tight text-zinc-900 dark:text-white">
                Nucleus
              </span>
            </a>

            <nav className="hidden items-center gap-7 text-sm font-medium text-zinc-600 md:flex dark:text-zinc-400">
              <a href="#features" className="transition-colors hover:text-zinc-900 dark:hover:text-white">
                功能
              </a>
              <a href="#pricing" className="transition-colors hover:text-zinc-900 dark:hover:text-white">
                定价
              </a>
              <a href="#docs" className="transition-colors hover:text-zinc-900 dark:hover:text-white">
                文档
              </a>
            </nav>

            <div className="flex items-center gap-3">
              <ThemeToggle />
              <a
                href="#start"
                className="hidden rounded-full bg-zinc-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-zinc-800 sm:inline-flex dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
              >
                开始使用
              </a>
            </div>
          </div>
        </header>

        <main>{children}</main>

        {/* 页脚 */}
        <footer className="border-t border-zinc-200 py-10 dark:border-zinc-800">
          <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-6 text-xs text-zinc-500 sm:flex-row lg:px-8 dark:text-zinc-500">
            <p>© 2026 Nucleus. 保留所有权利。</p>
            <div className="flex gap-6">
              <a href="#" className="transition-colors hover:text-zinc-900 dark:hover:text-zinc-300">
                隐私政策
              </a>
              <a href="#" className="transition-colors hover:text-zinc-900 dark:hover:text-zinc-300">
                服务条款
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}