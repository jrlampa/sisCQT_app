import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react' // Import the Babel-based React plugin

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react({
      // Add this line to enable Emotion's Babel plugin
      babel: {
        plugins: ['@emotion/babel-plugin'],
      },
    }),
  ],
})
