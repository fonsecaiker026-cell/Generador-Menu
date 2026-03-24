/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#fef2f2',
          100: '#fde8e8',
          200: '#fbd5d5',
          300: '#f8adad',
          400: '#f27878',
          500: '#e84949',
          600: '#d42b2b',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
          950: '#450a0a',
        },
        warm: {
          50:  '#fafaf8',
          100: '#f5f5f0',
          200: '#ededE5',
          300: '#e0ddd5',
          400: '#b8b4ac',
          500: '#908c84',
          600: '#706c64',
          700: '#5a5750',
          800: '#3d3b36',
          900: '#292724',
          950: '#1c1917',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'soft': '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        'card': '0 2px 8px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04)',
        'elevated': '0 8px 24px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)',
        'modal': '0 20px 60px rgba(0,0,0,0.15), 0 8px 24px rgba(0,0,0,0.08)',
      },
      animation: {
        'fade-in': 'fadeIn 0.15s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
        'scale-in': 'scaleIn 0.15s ease-out',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          from: { opacity: '0', transform: 'scale(0.96)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
}
