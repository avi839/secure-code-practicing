/** @type {import('tailwindcss').Config} */
// Visual system: "charging terminal on slate" (see docs/design-system.md).
// Charcoal neutrals, Slate Canvas #1c1e21 / Ink Well #121317, Signal Lime #a8ff53 accent.
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        charcoal: {
          100: '#e8e9ec',
          200: '#d7d9dd',
          300: '#b5b8c0',
          350: '#a4a8b0',
          400: '#878c99',
          500: '#5f6570',
          600: '#3b3e45',
          650: '#31353a',
          700: '#272a2e',
          750: '#212327',
          800: '#1a1b1f',
          850: '#15171a',
          900: '#121317',
          950: '#0d0e12',
          1000: '#0b0c0f',
        },
        apple: {
          300: '#bfff81',
          400: '#afff62',
          500: '#a8ff53',
          700: '#6fb12f',
          800: '#45711a',
          850: '#2e4e10',
        },
        canvas: '#1c1e21', // Slate Canvas
        ink: '#121317', // Ink Well (recessed: code, diff, terminal)
        hairline: '#3b3e45', // Graphite Hairline
        steel: '#272a2e', // Steel Border
        bone: '#e5e7eb', // primary text
        cloud: '#d7d9dd', // secondary headings / button text
        ash: '#b5b8c0', // tertiary text
        fog: '#878c99', // metadata / icon strokes (large text only)
        syntax: {
          violet: '#9c9af2',
          event: '#7655fd',
          pink: '#fa3abf',
          green: '#afec73',
          lime: '#d9f07c',
          magenta: '#e888f8',
        },
        mute: { red: '#f43f5e' },
        aqua: { DEFAULT: '#479dec', 600: '#3080e0', 700: '#276bce' },
        sev: {
          critical: '#f43f5e',
          high: '#fb923c',
          medium: '#fbbf24',
          low: '#479dec',
        },
      },
      fontFamily: {
        sans: ['Geist', 'Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        display: ['Satoshi', 'Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"Geist Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      fontSize: {
        code: ['14px', { lineHeight: '24px' }],
      },
      letterSpacing: {
        display: '0.025em',
        hero: '0.05em',
      },
      borderRadius: {
        xs: '2px',
        sm: '4px',
        DEFAULT: '4px',
        md: '6px',
        lg: '8px',
        xl: '12px',
      },
      transitionTimingFunction: {
        out: 'cubic-bezier(0, 0, .2, 1)',
        'in-out': 'cubic-bezier(.4, 0, .2, 1)',
      },
      keyframes: {
        enter: {
          from: { opacity: '0', transform: 'translateY(8px) scale(.98)' },
          to: { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        exit: {
          from: { opacity: '1', transform: 'translateY(0) scale(1)' },
          to: { opacity: '0', transform: 'translateY(8px) scale(.98)' },
        },
        marquee: {
          from: { transform: 'translateX(0)' },
          to: { transform: 'translateX(-50%)' },
        },
        'moving-lines': {
          from: { backgroundPosition: '-200% 0' },
          to: { backgroundPosition: '200% 0' },
        },
        'moving-lines-y': {
          from: { backgroundPosition: '0 -200%' },
          to: { backgroundPosition: '0 200%' },
        },
        rotation: {
          from: { '--glow-angle': '0deg' },
          to: { '--glow-angle': '360deg' },
        },
        opacityBlink: {
          '0%, 49%': { opacity: '1' },
          '50%, 100%': { opacity: '0' },
        },
        pulse: {
          '0%': { boxShadow: '0 0 0 0 rgba(168, 255, 83, .55)' },
          '70%': { boxShadow: '0 0 0 6px rgba(168, 255, 83, 0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(168, 255, 83, 0)' },
        },
        'pulse-ring': {
          '0%': { boxShadow: '0 0 0 0 rgba(135, 140, 153, .5)' },
          '70%': { boxShadow: '0 0 0 8px rgba(135, 140, 153, 0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(135, 140, 153, 0)' },
        },
        shimmer: {
          from: { backgroundPosition: '-200% 0' },
          to: { backgroundPosition: '200% 0' },
        },
        'accordion-down': {
          from: { height: '0', opacity: '0' },
          to: { height: 'var(--accordion-height)', opacity: '1' },
        },
        'accordion-up': {
          from: { height: 'var(--accordion-height)', opacity: '1' },
          to: { height: '0', opacity: '0' },
        },
        ripple: {
          from: { transform: 'scale(.4)', opacity: '.6' },
          to: { transform: 'scale(2.2)', opacity: '0' },
        },
      },
      animation: {
        enter: 'enter 300ms cubic-bezier(0, 0, .2, 1) both',
        'enter-slow': 'enter 700ms cubic-bezier(0, 0, .2, 1) both',
        exit: 'exit 200ms cubic-bezier(.4, 0, .2, 1) both',
        marquee: 'marquee 40s linear infinite',
        'moving-lines': 'moving-lines 2.4s linear infinite',
        'moving-lines-y': 'moving-lines-y 2.4s linear infinite',
        rotation: 'rotation 3s linear infinite',
        opacityBlink: 'opacityBlink 1s step-end infinite',
        pulse: 'pulse 1.8s cubic-bezier(0, 0, .2, 1) infinite',
        'pulse-ring': 'pulse-ring 1.6s cubic-bezier(0, 0, .2, 1) infinite',
        shimmer: 'shimmer 1.6s linear infinite',
        'accordion-down': 'accordion-down 220ms cubic-bezier(0, 0, .2, 1) both',
        'accordion-up': 'accordion-up 180ms cubic-bezier(.4, 0, .2, 1) both',
        ripple: 'ripple 500ms cubic-bezier(0, 0, .2, 1) both',
      },
    },
  },
  plugins: [],
}
