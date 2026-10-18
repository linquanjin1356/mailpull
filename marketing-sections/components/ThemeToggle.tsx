"use client";

import { useEffect, useState } from "react";

/**
 * 主题切换按钮
 * - 用 class 策略（<html class="dark">）
 * - 首屏由 layout 的内联脚本恢复，避免闪烁
 */
export default function ThemeToggle() {
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    const root = document.documentElement;
    root.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      /* 隐私模式下 localStorage 可能不可用，忽略 */
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? "切换到浅色模式" : "切换到深色模式"}
      aria-pressed={dark}
      className="inline-flex h-9 w-9 items-center justify-center rounded-full text-zinc-600 ring-1 ring-zinc-300 ring-inset transition-colors hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 dark:text-zinc-300 dark:ring-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-white dark:focus-visible:ring-white"
    >
      {/* 未挂载前渲染占位，避免服务端/客户端图标不一致导致 hydration 警告 */}
      {!mounted ? (
        <span className="h-4 w-4" />
      ) : dark ? (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
          <circle cx="12" cy="12" r="4" strokeLinecap="round" />
          <path d="M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6l1.4 1.4m10 10 1.4 1.4m0-12.8-1.4 1.4m-10 10-1.4 1.4" strokeLinecap="round" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
          <path d="M21 13.2A9 9 0 1 1 10.8 3a7 7 0 0 0 10.2 10.2z" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </button>
  );
}