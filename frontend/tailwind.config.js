/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // Semantic Colors (mapping to CSS variables)
                'brand': {
                    primary: 'var(--brand-primary)',
                    hover: 'var(--brand-hover)',
                    light: 'var(--brand-light)',
                    text: 'var(--brand-text)',
                },
                'bg': {
                    canvas: 'var(--bg-canvas)',
                    surface: 'var(--bg-surface)',
                    'surface-hover': 'var(--bg-surface-hover)',
                    modal: 'var(--bg-modal)',
                },
                'text': {
                    primary: 'var(--text-primary)',
                    secondary: 'var(--text-secondary)',
                    tertiary: 'var(--text-tertiary)',
                },
                'border': {
                    light: 'var(--border-light)',
                    medium: 'var(--border-medium)',
                },
                'status': {
                    success: 'var(--status-success)',
                    error: 'var(--status-error)',
                    warning: 'var(--status-warning)',
                },

                // Legacy support (optional, if you want to keep old names working temporarily)
                primary: {
                    50: '#f0f9ff',
                    100: '#e0f2fe',
                    200: '#bae6fd',
                    300: '#7dd3fc',
                    400: '#38bdf8',
                    500: '#0ea5e9',
                    600: '#0284c7',
                    700: '#0369a1',
                    800: '#075985',
                    900: '#0c4a6e',
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'monospace'],
                display: ['Outfit', 'sans-serif'],
            },
            animation: {
                'fade-in': 'fadeIn 0.3s ease-out',
                'slide-up': 'slideUp 0.3s ease-out',
                'pulse-soft': 'pulseSoft 2s infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                pulseSoft: {
                    '0%, 100%': { opacity: '1' },
                    '50%': { opacity: '0.5' },
                },
            },
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
    ],
}
