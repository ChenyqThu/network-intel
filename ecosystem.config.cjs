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
//
// nintel-dev is a local-only Vite dev server (HMR) at localhost:5174: edit a
// .tsx/.css file under apps/web/src and the browser updates instantly, no
// rebuild. It proxies /api -> 8000, so it reads the SAME live backend data as
// prod. Not tunneled (local preview only).
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
    {
      // davmail OAuth bridge: local SMTP 1025 / IMAP 1143 -> Exchange, in Docker.
      // Powers `nintel.pipeline send` (email send / draft). Needs a one-time
      // token.dat — see apps/api/infra/davmail/README.md. Bound to 127.0.0.1 only.
      name: 'nintel-davmail',
      cwd: path.join(ROOT, 'apps/api/infra/davmail'),
      script: 'run-davmail.sh',
      interpreter: 'none', // executable sh script (shebang)
      autorestart: true,
      max_restarts: 10,
    },
    {
      name: 'nintel-dev',
      cwd: path.join(ROOT, 'apps/web'),
      script: 'node_modules/.bin/vite',
      // Dev server with HMR (on-the-fly transforms, no build step). Local only
      // at localhost:5174 (5173 is the prod preview). Edit src/** -> instant
      // reload. Proxies /api -> 8000 (same live backend as prod).
      args: '--port 5174 --strictPort',
      interpreter: 'none',
      autorestart: true,
      max_restarts: 10,
    },
  ],
};
