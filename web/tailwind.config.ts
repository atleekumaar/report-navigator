import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#0B0D12",
        surface: "#12151C",
        surfaceBorder: "rgba(255, 255, 255, 0.08)",
        surfaceHover: "#1A1E27",
        accent: {
          DEFAULT: "#6366F1",
          hover: "#4F46E5",
          purple: "#8B5CF6",
        },
        verified: "#22C55E",
        warning: "#F59E0B",
        danger: "#EF4444",
        highlight: "rgba(253, 224, 71, 0.35)",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
      borderRadius: {
        card: "14px",
      },
      animation: {
        pulseHighlight: "pulseHighlight 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        pulseHighlight: {
          "0%, 100%": { opacity: "0.35", transform: "scale(1)" },
          "50%": { opacity: "0.7", transform: "scale(1.01)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;

