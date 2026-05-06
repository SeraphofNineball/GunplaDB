/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        gundam: {
          red: '#C0392B',
          blue: '#2C3E7A',
          dark: '#1A1A2E',
          card: '#16213E',
          border: '#0F3460',
        },
      },
    },
  },
  plugins: [],
}
