/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Palette "instrument de précision" — papier chaud, jamais noir/violet/bleu nuit.
        paper: {
          DEFAULT: "#FAF8F3", // fond principal
          card: "#FFFFFF",    // surfaces de carte
          line: "#E4E0D6",    // hairlines / séparateurs
        },
        ink: {
          DEFAULT: "#1C1B19", // texte principal — presque noir mais chaud, jamais froid
          soft: "#6B6A64",    // texte secondaire
          faint: "#A6A399",   // texte tertiaire / placeholders
        },
        signal: {
          authorized: "#173404", // vert profond — autorisé / positif
          watch: "#9C6B14",      // ambre / moutarde — surveiller
          weak: "#8A6A1F",       // ambre plus terne — faible
          rejected: "#7A1F1F",   // rouge brique — rejeté / négatif
        },
      },
      fontFamily: {
        display: ["'Fraunces'", "serif"],
        sans: ["'Inter'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
    },
  },
  plugins: [],
};


