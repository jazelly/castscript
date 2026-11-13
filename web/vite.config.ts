import AgenticReact from '@agentic-react/vite';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  // AgenticReact adds the dev-only toolbox and MCP endpoint (/mcp) so coding agents can see and pick UI elements.
  plugins: [react(), tailwindcss(), AgenticReact()],
  // `castscript web` serves the built app from the Python package.
  build: { outDir: '../castscript/webui', emptyOutDir: true },
  // In development the API comes from `castscript web` on its default port.
  server: { port: 5174, strictPort: true, proxy: { '/api': 'http://127.0.0.1:47810' } },
});
