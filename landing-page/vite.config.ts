import { defineConfig, type Plugin } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

// Stub figma:asset/ imports with a 1x1 transparent PNG data URI for local dev
function figmaAssetStub(): Plugin {
  return {
    name: 'figma-asset-stub',
    resolveId(id) {
      if (id.startsWith('figma:asset/')) {
        return '\0' + id;
      }
    },
    load(id) {
      if (id.startsWith('\0figma:asset/')) {
        return `export default "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPj/HwADBwIAMCbHYQAAAABJRU5ErkJggg=="`;
      }
    },
  };
}

export default defineConfig({
  plugins: [
    figmaAssetStub(),
    // The React and Tailwind plugins are both required for Make, even if
    // Tailwind is not being actively used – do not remove them
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      // Alias @ to the src directory
      '@': path.resolve(__dirname, './src'),
    },
  },

  // File types to support raw imports. Never add .css, .tsx, or .ts files to this.
  assetsInclude: ['**/*.svg', '**/*.csv'],

  // Server configuration
  server: {
    port: 3000,
  },
})
