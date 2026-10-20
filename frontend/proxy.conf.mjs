// ng serve forwards the WebSocket to the backend: localhost:8000 on the host,
// http://backend:8000 inside docker compose (BACKEND_URL).
export default {
  '/ws': {
    target: process.env.BACKEND_URL ?? 'http://localhost:8000',
    ws: true,
    changeOrigin: true,
  },
};
