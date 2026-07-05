import type { Config } from 'tailwindcss';

export default {
  content: [
    './src/renderer/index.html',
    './src/renderer/**/*.{js,ts,jsx,tsx}',
  ],

  darkMode: 'class',

  theme: {
    extend: {
      // ===== Custom Design System =====

      colors: {
        // Primary brand colors
        primary: {
          50: '#EEF2FF',
          100: '#E0E7FF',
          200: '#C7D2FE',
          300: '#A5B4FC',
          400: '#818CF8',
          500: '#6366F1',
          600: '#4F46E5',
          700: '#4338CA',
          800: '#3730A3',
          900: '#312E81',
          950: '#1E1B4B',
        },

        // Neutral grays for UI surfaces
        surface: {
          50: '#F8FAFC',
          100: '#F1F5F9',
          200: '#E2E8F0',
          300: '#CBD5E1',
          400: '#94A3B8',
          500: '#64748B',
          600: '#475569',
          700: '#334155',
          800: '#1E293B',
          900: '#0F172A',
          950: '#020617',
        },

        // Semantic status colors
        status: {
          success: '#22C55E',
          warning: '#F59E0B',
          error: '#EF4444',
          info: '#3B82F6',
        },

        // Agent role colors
        agent: {
          developer: '#3B82F6',
          reviewer: '#8B5CF6',
          fixer: '#F59E0B',
          tester: '#22C55E',
          deployer: '#06B6D4',
        },

        // Workflow state colors
        workflow: {
          pending: '#94A3B8',
          running: '#3B82F6',
          reviewing: '#8B5CF6',
          fixing: '#F59E0B',
          testing: '#22C55E',
          completed: '#10B981',
          failed: '#EF4444',
        },

        // Canvas / editor backgrounds
        canvas: {
          bg: '#1A1A2E',
          grid: '#16213E',
          node: '#0F3460',
          edge: '#E94560',
        },
      },

      // Custom font families
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', 'monospace'],
        display: ['Cal Sans', 'Inter', 'system-ui', 'sans-serif'],
      },

      // Custom spacing scale aligned to 4px grid
      spacing: {
        '4.5': '1.125rem',
        '13': '3.25rem',
        '15': '3.75rem',
        '18': '4.5rem',
        '22': '5.5rem',
        '26': '6.5rem',
        '30': '7.5rem',
        '34': '8.5rem',
        '38': '9.5rem',
        '42': '10.5rem',
        '50': '12.5rem',
        '60': '15rem',
        '70': '17.5rem',
        '84': '21rem',
        '100': '25rem',
        '120': '30rem',
      },

      // Custom border radius
      borderRadius: {
        '4xl': '2rem',
        '5xl': '2.5rem',
      },

      // Custom animation keyframes
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-out': {
          '0%': { opacity: '1', transform: 'translateY(0)' },
          '100%': { opacity: '0', transform: 'translateY(4px)' },
        },
        'slide-in-right': {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        'slide-out-right': {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(100%)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        'spin-slow': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        'node-enter': {
          '0%': { opacity: '0', transform: 'scale(0.9)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },

      animation: {
        'fade-in': 'fade-in 0.2s ease-out',
        'fade-out': 'fade-out 0.2s ease-in',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
        'slide-out-right': 'slide-out-right 0.3s ease-in',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
        'spin-slow': 'spin-slow 3s linear infinite',
        'node-enter': 'node-enter 0.3s ease-out',
      },

      // Custom box shadows
      boxShadow: {
        'glow-primary': '0 0 15px rgba(99, 102, 241, 0.3)',
        'glow-success': '0 0 15px rgba(34, 197, 94, 0.3)',
        'glow-error': '0 0 15px rgba(239, 68, 68, 0.3)',
        'node': '0 4px 20px rgba(0, 0, 0, 0.25)',
        'node-hover': '0 8px 30px rgba(0, 0, 0, 0.35)',
        'panel': '0 2px 12px rgba(0, 0, 0, 0.08)',
        'panel-dark': '0 2px 12px rgba(0, 0, 0, 0.3)',
      },

      // Custom z-index scale
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
        '90': '90',
        '100': '100',
        'max': '9999',
      },
    },
  },

  plugins: [],
} satisfies Config;
