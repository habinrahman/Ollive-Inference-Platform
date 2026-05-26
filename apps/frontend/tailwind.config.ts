import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#f8fafc",
        panel: "#ffffff",
        border: "#e4e4e7"
      }
    }
  },
  plugins: []
};

export default config;
