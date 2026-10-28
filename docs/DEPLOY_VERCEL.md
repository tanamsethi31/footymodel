# Vercel deployment (footymodel dashboard)

The Next.js app lives in **`dashboard/`**, not the repo root. GitHub pushes trigger a Vercel production deploy.

## If builds fail with “No Next.js version detected”

In [Vercel → Project Settings → General → Root Directory](https://vercel.com/docs/deployments/configure-a-build#root-directory), set:

**Root Directory:** `dashboard`

Alternatively, the repo root **`vercel.json`** runs `cd dashboard && npm run build` when Root Directory is left empty.

## Required environment variables (Vercel → Settings → Environment Variables)

| Variable | Purpose |
|----------|---------|
| **`GITHUB_TOKEN`** | Read `data/processed/*` from the private repo at runtime (and during static generation). Without it, the site builds but shows empty data. |
| **`NOTIFY_SECRET`** | `/api/notify` auth (must match GitHub Actions `NOTIFY_SECRET`) |
| **`VAPID_*` / Upstash** | Web Push + subscription storage (see dashboard env) |

Use a fine-scoped PAT or GitHub App token with **Contents: read** on `tanamsethi31/footymodel`.

## Common failure modes

1. **Root Directory unset** — Vercel builds from repo root (no `package.json` / no Next app).
2. **`GITHUB_TOKEN` missing or 401/403** — build used to throw on fetch errors; now degrades to empty sections (fixed in `lib/data.ts`).
3. **Serverless bundle too large** — caused by reading `../data/processed` on Vercel; local file reads are disabled when `VERCEL=1`.

After fixing settings, redeploy from Vercel → Deployments → **Redeploy** latest `main`.
