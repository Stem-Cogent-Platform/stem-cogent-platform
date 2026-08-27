import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        page: "var(--bg-page)", surface: "var(--bg-surface)", subtle: "var(--bg-subtle)",
        ink: "var(--text-primary)", muted: "var(--text-secondary)", border: "var(--border)", cobalt: "var(--accent)"
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] }
    }
  },
  plugins: []
};

export default config;
