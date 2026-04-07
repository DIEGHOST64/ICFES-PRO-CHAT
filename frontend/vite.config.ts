import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('plotly.js') || id.includes('react-plotly.js')) return 'plotly'
          if (id.includes('katex') || id.includes('react-katex')) return 'katex'
          if (id.includes('gsap') || id.includes('@gsap/react')) return 'gsap'
          if (id.includes('axios')) return 'network'
          if (id.includes('lucide-react')) return 'icons'
          return 'vendor'
        },
      },
    },
  },
})
