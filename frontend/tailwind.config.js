/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                alabaster: '#F9F8F6',
                charcoal: '#1A1A1A',
                gold: '#D4AF37',
                'warm-grey': '#6C6863',
                'pale-taupe': '#EBE5DE',
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                serif: ['Playfair Display', 'serif'],
            },
            transitionDuration: {
                '2000': '2000ms',
            },
            animation: {
                'fade-in': 'fade-in 0.7s ease-out forwards',
                'slide-up': 'slide-up 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards',
                'reveal': 'reveal 1.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards',
            },
            keyframes: {
                'fade-in': {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                'slide-up': {
                    '0%': { opacity: '0', transform: 'translateY(20px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                'reveal': {
                    '0%': { opacity: '0', filter: 'blur(10px)' },
                    '100%': { opacity: '1', filter: 'blur(0)' },
                }
            }
        },
    },
    plugins: [],
}
