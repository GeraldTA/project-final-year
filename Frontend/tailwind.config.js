/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'theme': {
          'bg': 'var(--theme-bg)',
          'card': 'var(--theme-card)',
          'primary': 'var(--theme-primary)',
          'secondary': 'var(--theme-secondary)',
          'accent': 'var(--theme-accent)',
          'border': 'var(--theme-border)',
          'hover': 'var(--theme-hover)',
          'text': {
            'primary': 'var(--theme-text-primary)',
            'secondary': 'var(--theme-text-secondary)',
          }
        }
      }
    },
  },
  plugins: [],
};
