// pm2 process definitions for Network Intel local services.
//
//   pm2 start ecosystem.config.cjs   # start both
//   pm2 save                         # persist across daemon restarts
//   pm2 logs nintel-web              # tail logs
//   pm2 restart nintel-api           # restart one
//
// The pm2 daemon runs independently of any terminal/Claude session, so these
// stay up after you close the shell. Cloudflare tunnel forwards:
//   daily.omada.ink -> localhost:5173 (web) -> proxies /api -> localhost:8000
const path = require('path');
const ROOT = __dirname;

module.exports = {
  apps: [
    {
      name: 'nintel-api',
      cwd: path.join(ROOT, 'apps/api'),
      script: '.venv/bin/python',
      args: '-m uvicorn nintel.api.app:app --host 127.0.0.1 --port 8000',
      interpreter: 'none', // run the venv python directly, not via node
      autorestart: true,
      max_restarts: 10,
      env: { PYTHONUNBUFFERED: '1' },
    },
    {
      name: 'nintel-web',
      cwd: path.join(ROOT, 'apps/web'),
      script: 'node_modules/.bin/vite',
      // Serve the optimized production build from dist/ (run `npm run build`
      // first). --strictPort fails loudly instead of drifting to 5174, which
      // would silently break the tunnel target.
      args: 'preview --port 5173 --strictPort',
      interpreter: 'none', // vite has its own node shebang
      autorestart: true,
      max_restarts: 10,
    },
  ],
};
