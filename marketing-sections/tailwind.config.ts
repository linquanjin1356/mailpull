import type { Config } from "tailwindcss";

const config: Config = {
  // class 策略：由 <html class="dark"> 控制，方便做主题切换按钮
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      // 保证正文/标题在各主题下的对比度都达到 WCAG AA (>= 4.5:1)
      colors: {},
    },
  },
  plugins: [],
};

export default config;