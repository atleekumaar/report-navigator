/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#1A0312",
        maroon: {
          950: "#14010E",
          900: "#220217",
          850: "#2C051E",
          800: "#3B0A25",
          700: "#540D34",
          600: "#6B1240",
          500: "#8C1B56",
        },
        surface: "rgba(45, 8, 30, 0.72)",
        surfaceBorder: "rgba(255, 110, 165, 0.22)",
        surfaceHover: "rgba(75, 15, 50, 0.82)",
        accent: {
          DEFAULT: "#F0508C",
          hover: "#FF7AA8",
          light: "#FFA3C5",
          purple: "#B83280",
          gradientStart: "#FF6EA7",
          gradientEnd: "#E02875",
        },
        blush: {
          DEFAULT: "#F6C4D0",
          light: "#FDEDF2",
          muted: "#D4A5B8",
        },
        verified: "#10B981",
        warning: "#F59E0B",
        danger: "#EF4444",
        highlight: "rgba(255, 105, 180, 0.4)",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
      borderRadius: {
        card: "16px",
      },
      boxShadow: {
        glow: "0 0 20px -3px rgba(240, 80, 140, 0.35)",
        "glow-lg": "0 0 35px -5px rgba(240, 80, 140, 0.45)",
        glass: "0 8px 32px 0 rgba(15, 0, 10, 0.45)",
      },
      backdropBlur: {
        xs: "2px",
      },
      animation: {
        pulseHighlight: "pulseHighlight 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        float: "float 6s ease-in-out infinite",
        pulseGlow: "pulseGlow 3s ease-in-out infinite",
      },
      keyframes: {
        pulseHighlight: {
          "0%, 100%": { opacity: "0.35", transform: "scale(1)" },
          "50%": { opacity: "0.7", transform: "scale(1.01)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
        pulseGlow: {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};
