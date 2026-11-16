/** @type {import('tailwindcss').Config} */
const v = (nome) => `rgb(var(--${nome}) / <alpha-value>)`;
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        tinta: { DEFAULT: v("tinta"), 2: v("tinta-2"), 3: v("tinta-3") },
        papel: v("papel"), folha: v("folha"), linha: v("linha"),
        pedra: { DEFAULT: v("pedra"), fundo: v("pedra-fundo"), forte: v("pedra-forte") },
        falcao: { DEFAULT: v("falcao"), fundo: v("falcao-fundo") },
        alerta: { DEFAULT: v("alerta"), fundo: v("alerta-fundo") },
        erro: { DEFAULT: v("erro"), fundo: v("erro-fundo") },
        info: { DEFAULT: v("info"), fundo: v("info-fundo") },
      },
      fontFamily: {
        titulo: ['"Bricolage"', '"Segoe UI"', "system-ui", "sans-serif"],
        texto: ['"Instrument"', '"Segoe UI"', "system-ui", "sans-serif"],
      },
      borderRadius: { caixa: "14px" },
      boxShadow: { caixa: "0 1px 2px rgb(16 24 20 / 0.04), 0 4px 16px rgb(16 24 20 / 0.04)" },
    },
  },
  plugins: [],
};
