/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        base: "#0B0A1A",
        surface: "#14122B",
        "surface-hi": "#1D1A3D",
        border: "#2A2650",
        accent: "#7C6FF0",
        "accent-soft": "#4C4499",
        good: "#4ADE80",
        warn: "#F5A623",
        bad: "#F87171",
        ink: "#F1F0FA",
        muted: "#8B87B0",
      },
      fontFamily: {
        display: [
          "-apple-system", "BlinkMacSystemFont", "Segoe UI", "system-ui", "sans-serif",
        ],
        body: [
          "-apple-system", "BlinkMacSystemFont", "Segoe UI", "system-ui", "sans-serif",
        ],
        mono: [
          "ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "Liberation Mono", "monospace",
        ],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(124,111,240,0.35), 0 8px 30px -8px rgba(124,111,240,0.45)",
      },
    },
  },
  plugins: [],
};
