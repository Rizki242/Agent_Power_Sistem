/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        panel: "var(--panel)",
        panel2: "var(--panel-2)",
        line: "var(--line)",
        textMain: "var(--text-main)",
        muted: "var(--muted)",
        cyan: "var(--cyan)",
        green: "var(--green)",
        amber: "var(--amber)",
        red: "var(--red)",
        purple: "var(--purple)",
        blue: "var(--blue)",
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'hero-gradient': 'var(--hero-grad)',
        'card-gradient': 'var(--card-grad)',
      },
      boxShadow: {
        'neon': 'var(--shadow-neon)',
      }
    },
  },
  plugins: [],
}
