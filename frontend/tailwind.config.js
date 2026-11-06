/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // New dark design system
        'mm-base':     '#080808',
        'mm-surface':  '#0f0f0f',
        'mm-elevated': '#161616',
        'mm-hover':    '#1c1c1c',
        'mm-border':   'rgba(255,255,255,0.06)',
        'mm-text':     '#f2f2f2',
        'mm-muted':    '#808080',
        'mm-accent':   '#e8603c',
        // Legacy (kept for backward compat)
        terra:   { DEFAULT: '#e8603c', light: '#D4806A', dark: '#d4522f', muted: '#e8603c' },
        olive:   { DEFAULT: '#5C7A2E', light: '#7A9E42', dark: '#3F5420', muted: '#F0F4E8' },
        navy:    { DEFAULT: '#2A4A6B', light: '#4A6A8B', dark: '#1A2F45' },
        cream:   { DEFAULT: '#F4EDE0', dark: '#DDD0BC', deeper: '#C8B89A' },
        sand:    { DEFAULT: '#2A1F14', mid: '#6B5240', light: '#A08878', lighter: '#C4B5A8' },
      },
      fontFamily: {
        sans:    ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['"Playfair Display"', 'Georgia', 'serif'],
        playfair:['"Playfair Display"', 'Georgia', 'serif'],
      },
      borderRadius: {
        xl:    '1rem',
        '2xl': '1.25rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      boxShadow: {
        'glow-sm':  '0 0 12px rgba(232,96,60,0.2)',
        'glow-md':  '0 0 24px rgba(232,96,60,0.25)',
        'glow-lg':  '0 0 40px rgba(232,96,60,0.15)',
        'surface':  '0 0 0 1px rgba(255,255,255,0.06)',
        'elevated': '0 0 0 1px rgba(255,255,255,0.09), 0 8px 24px rgba(0,0,0,0.4)',
        'modal':    '0 0 0 1px rgba(255,255,255,0.09), 0 24px 64px rgba(0,0,0,0.6)',
        // Legacy
        card:        '0 1px 3px rgba(0,0,0,0.2), 0 4px 16px rgba(0,0,0,0.3)',
        'card-hover':'0 1px 3px rgba(0,0,0,0.3), 0 12px 32px rgba(0,0,0,0.4)',
        glass:       '0 1px 2px rgba(0,0,0,0.2)',
        button:      '0 1px 2px rgba(0,0,0,0.2), 0 2px 8px rgba(232,96,60,0.20)',
        'button-hover':'0 2px 4px rgba(0,0,0,0.3), 0 4px 16px rgba(232,96,60,0.28)',
        float:       '0 4px 12px rgba(0,0,0,0.4), 0 16px 40px rgba(0,0,0,0.3)',
        'float-hover':'0 8px 20px rgba(0,0,0,0.5), 0 24px 48px rgba(0,0,0,0.4)',
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        smooth: 'cubic-bezier(0.4, 0, 0.2, 1)',
        out:    'cubic-bezier(0, 0, 0.2, 1)',
        bounce: 'cubic-bezier(0.23, 1, 0.32, 1)',
      },
      keyframes: {
        fadeInUp: {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(24px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        slideDown: {
          '0%':   { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%':   { opacity: '0', transform: 'scale(0.94)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        modalIn: {
          '0%':   { opacity: '0', transform: 'translateY(8px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        kcalPulse: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%':      { transform: 'scale(1.05)' },
        },
        barGrow: {
          '0%':   { width: '0%' },
          '100%': { width: 'var(--bar-w)' },
        },
        scanLine: {
          '0%':   { top: '0%',   opacity: '0.9' },
          '50%':  { opacity: '1' },
          '100%': { top: '100%', opacity: '0.9' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-400px 0' },
          '100%': { backgroundPosition: ' 400px 0' },
        },
        breathe: {
          '0%, 100%': { transform: 'scale(1)',    opacity: '0.8' },
          '50%':      { transform: 'scale(1.04)', opacity: '1'   },
        },
        progressBar: {
          '0%':   { width: '0%',  opacity: '1'   },
          '80%':  { width: '85%', opacity: '1'   },
          '100%': { width: '92%', opacity: '0.8' },
        },
        countUp: {
          '0%':   { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in-up':  'fadeInUp 0.40s cubic-bezier(0.16, 1, 0.3, 1) both',
        'fade-in':     'fadeIn   0.25s ease-out both',
        'slide-up':    'slideUp  0.40s cubic-bezier(0.16, 1, 0.3, 1) both',
        'slide-down':  'slideDown 0.20s cubic-bezier(0.16, 1, 0.3, 1) both',
        'scale-in':    'scaleIn  0.25s cubic-bezier(0.34, 1.56, 0.64, 1) both',
        'modal-in':    'modalIn  0.30s cubic-bezier(0.16, 1, 0.3, 1) both',
        'kcal-pulse':  'kcalPulse 0.35s ease-in-out',
        'scan-line':   'scanLine 2s ease-in-out infinite',
        'breathe':     'breathe 3s ease-in-out infinite',
        'progress':    'progressBar 9s ease-out forwards',
      },
    },
  },
  plugins: [],
}
