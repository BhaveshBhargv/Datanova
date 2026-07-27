/** @type {import('tailwindcss').Config} */

// "Plasma Observatory" — plasma-magenta nova on cool ink/paper, with a gold spark.
const nova = {
  50: "#FDF2FA",
  100: "#FCE7F4",
  200: "#FBCEEA",
  300: "#F7A6D8",
  400: "#F06CBE",
  500: "#E23AA3",
  600: "#C51E8A",
  700: "#A31672",
  800: "#84115C",
  900: "#6B0E4B",
};

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        nova,
        indigo: nova, // re-skin any legacy indigo usage to the nova accent
        spark: "#F6B01E", // gold — starlight, used sparingly
        signal: "#0E9E9E", // teal — positive / secondary data
        ink: {
          DEFAULT: "#111524",
          soft: "#1B2135",
          800: "#1B2135",
          900: "#0C0F1A",
        },
        paper: "#F4F5F8",
        line: "#E5E6EC",
      },
      fontFamily: {
        sans: ['"Inter"', "system-ui", "sans-serif"],
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        mono: ['"Space Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(17,21,36,0.04), 0 8px 24px -12px rgba(17,21,36,0.10)",
        nova: "0 8px 30px -8px rgba(197,30,138,0.45)",
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.125rem",
      },
      keyframes: {
        "spark-pulse": {
          "0%,100%": { opacity: "0.5", transform: "scale(0.92)" },
          "50%": { opacity: "1", transform: "scale(1.05)" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "spark-pulse": "spark-pulse 3.5s ease-in-out infinite",
        "fade-up": "fade-up 0.5s ease-out both",
      },
    },
  },
  plugins: [],
};
