import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        primary: "hsl(var(--primary))",
        "primary-foreground": "hsl(var(--primary-foreground))",
        accent: "hsl(var(--accent))",
        "accent-foreground": "hsl(var(--accent-foreground))",
        destructive: "hsl(var(--destructive))",
        "destructive-foreground": "hsl(var(--destructive-foreground))",
        ring: "hsl(var(--ring))",
        neon: {
          DEFAULT: "#a855f7",
          soft: "#c084fc",
          deep: "#7c3aed",
          glow: "rgba(168,85,247,0.45)",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xl: "calc(var(--radius) + 4px)",
      },
      boxShadow: {
        neon: "0 0 18px rgba(168,85,247,0.55), 0 0 64px rgba(124,58,237,0.25)",
        card: "0 8px 30px rgba(0,0,0,0.35)",
      },
      backgroundImage: {
        "neon-grad":
          "linear-gradient(135deg, #7c3aed 0%, #a855f7 45%, #d946ef 100%)",
        "card-grad":
          "linear-gradient(160deg, rgba(168,85,247,0.18) 0%, rgba(20,16,33,0.6) 60%, rgba(10,9,17,0.9) 100%)",
        "page-grad":
          "radial-gradient(60% 60% at 20% 0%, rgba(124,58,237,0.25) 0%, rgba(10,9,17,0) 60%), radial-gradient(80% 60% at 90% 10%, rgba(217,70,239,0.18) 0%, rgba(10,9,17,0) 60%), linear-gradient(180deg, #0a0911 0%, #0a0911 100%)",
      },
      keyframes: {
        "fade-in": { "0%": { opacity: "0", transform: "translateY(6px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        glow: {
          "0%,100%": { boxShadow: "0 0 12px rgba(168,85,247,0.4)" },
          "50%": { boxShadow: "0 0 28px rgba(168,85,247,0.85)" },
        },
      },
      animation: {
        "fade-in": "fade-in 200ms ease-out",
        glow: "glow 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
