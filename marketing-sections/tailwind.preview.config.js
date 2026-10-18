/** 仅用于把 preview.html 的 Tailwind 样式离线编译，不进正式项目构建 */
const config = {
  darkMode: "class",
  content: ["../preview.html"],
  theme: { extend: {} },
  plugins: [],
};

export default config;