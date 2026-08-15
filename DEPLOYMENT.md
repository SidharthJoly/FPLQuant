# Deploying the backend (Oracle Cloud "Always Free")

The frontend deploys itself (GitHub Pages, see `.github/workflows/pages.yml`).
This covers the backend: FastAPI + Redis, via `docker-compose.yml`, on an
Oracle Cloud "Always Free" VM.

## 1. Create the VM

1. Sign up at [cloud.oracle.com](https://cloud.oracle.com) (needs a card for
   identity verification; the Always Free resources below don't charge it).
2. Create a compute instance:
   - **Shape:** `VM.Standard.A1.Flex` (Ampere/ARM) — the generous Always Free
     tier (up to 4 OCPUs / 24GB RAM total across your Always Free instances).
     The Dockerfile here builds fine on ARM (`python:3.13-slim` and the uv
     base image are both multi-arch), so this is the recommended shape over
     the much smaller AMD micro shapes.
   - **Image:** Ubuntu (latest LTS).
   - **Networking:** note the public IP. In the VCN's security list (or the
     instance's attached NSG), add ingress rules for TCP 22 (SSH), 80, and
     443 from `0.0.0.0/0`. Oracle's default security list blocks 80/443 by
     default — this step is easy to miss.
3. Add your SSH public key during instance creation (or after, via the
   console's "Add SSH Keys" action).

## 2. First-time server setup

SSH in (`ssh ubuntu@<public-ip>`) and install Docker:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # or log out/in
```

Clone the repo and start the stack:

```bash
git clone https://github.com/SidharthJoly/FPLQuant.git
cd FPLQuant
cp .env.example .env
# Edit .env: set FPLQUANT_CORS_ALLOWED_ORIGINS to include the Pages origin
# (https://sidharthjoly.github.io) plus your custom domain once it exists.
docker compose up -d --build
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run fplquant-ingest
```

Confirm it's up: `curl http://localhost:8000/health` should return `{"status":"ok"}`.

## 3. Point the frontend at it

Edit `frontend/config.js`:

```js
export const API_BASE = "http://<public-ip>:8000";  // or https://your-domain once set up
```

Commit and push — `.github/workflows/pages.yml` redeploys the Pages site
automatically on any push touching `frontend/`.

## 4. HTTPS + custom domain (once the Student Pack domain exists)

Point the domain's DNS A record at the VM's public IP, then add a reverse
proxy for automatic HTTPS. [Caddy](https://caddyserver.com/) is the simplest
option — one binary, automatic Let's Encrypt certs, ~5 lines of config:

```
# /etc/caddy/Caddyfile (after `sudo apt install caddy`)
api.your-domain.com {
    reverse_proxy localhost:8000
}
```

`sudo systemctl restart caddy` and Caddy handles cert issuance/renewal on its
own. Then update `frontend/config.js`'s `API_BASE` to `https://api.your-domain.com`
and `FPLQUANT_CORS_ALLOWED_ORIGINS` in `.env` to match.

## 5. Redeploying after changes (CD)

`.github/workflows/deploy.yml` SSHes into the VM and re-pulls/rebuilds —
manually triggered (`workflow_dispatch`), not on every push, so a deploy is
always a deliberate action. Needs these repo secrets set first
(Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | the VM's public IP or domain |
| `DEPLOY_USER` | `ubuntu` (or whatever user you SSH in as) |
| `DEPLOY_SSH_KEY` | the private key matching the public key added to the instance |

Then: Actions tab → "Deploy backend" → Run workflow.

## Scheduled data ingest on the server

The GitHub Actions ingest workflows (`.github/workflows/ingest*.yml`) run in
CI and upload the resulting SQLite DB as a build artifact — they don't touch
the deployed server automatically. To keep the live server's data fresh,
either:
- run `docker compose exec api uv run fplquant-ingest` (and
  `fplquant-ingest-injuries`) via cron on the VM itself, or
- extend the CD workflow to download the latest ingest artifact and swap it
  in.

Not wired up yet — worth doing once the server is live and this becomes a
real (not hypothetical) staleness problem.
