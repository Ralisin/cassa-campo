/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter Variable',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
      colors: {
        forest: '#12372a',
        moss: '#436850',
        cream: '#f4f1e8',
        amber: '#d59d2b',
      },
      boxShadow: {
        card: '0 16px 40px -28px rgba(18, 55, 42, 0.45)',
      },
    },
  },
  plugins: [],
}
