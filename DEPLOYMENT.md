# Deploying the backend (Oracle Cloud "Always Free")

The frontend deploys itself (GitHub Pages, see `.github/workflows/pages.yml`),
live at https://sidharthjoly.github.io/FPLQuant/.

The backend (FastAPI + Redis, via `docker-compose.yml`) is **live** on an
Oracle Cloud "Always Free" VM, fronted by Caddy for HTTPS:

```
Browser (GitHub Pages, HTTPS)
        │
        ▼
https://fplquant.duckdns.org   ── DuckDNS: free, permanent subdomain
        │
        ▼
Caddy (:80/:443 on the VM)     ── automatic Let's Encrypt cert, auto-renewing
        │
        ▼
FastAPI (localhost:8000, in Docker)
```

DigitalOcean's GitHub Student Pack offer expired (2026-07-31) before it was
redeemed, so this uses Oracle's Always Free tier instead — and DuckDNS +
Caddy rather than a purchased domain, since it's genuinely free with no
renewal hassle (unlike some free-DNS providers that require confirming a
link every 30 days) and Let's Encrypt certs are free and auto-renewing
indefinitely. No dependency on any time-limited credit or trial.

This doc is both a record of the current setup and a runbook for recreating
it (e.g. if the VM is ever lost and needs rebuilding from scratch).

## 1. Create the VM

1. Sign up at [cloud.oracle.com](https://cloud.oracle.com) (needs a card for
   identity verification; the Always Free resources below don't charge it).
2. Create a compute instance:
   - **Shape:** `VM.Standard.A1.Flex` (Ampere/ARM) is the most generous
     Always Free shape, but ARM capacity can be unavailable in some regions
     — `VM.Standard.E2.1.Micro` (AMD, x86_64, 1/8 OCPU, 1GB RAM) is the
     reliable fallback and is what's actually running today. The Dockerfile
     builds fine on either architecture.
   - **Image:** Ubuntu (latest LTS).
   - **Networking:** create a new VCN + public subnet (the instance-creation
     wizard's default), with **"Automatically assign public IPv4 address"
     enabled** — it can silently end up unchecked, worth double-checking
     before creating. If the instance ends up with no public IP anyway, add
     an **ephemeral** public IP afterward via the VNIC's IP Addresses page.
   - **SSH keys:** paste an existing public key (`cat ~/.ssh/id_ed25519.pub`)
     rather than leaving "No SSH keys" selected — easy to miss and there's
     no good way to add one after the fact.
3. **Open the firewall — in two separate places, both required:**
   - **Cloud-level:** the subnet's Security List *and* any Network Security
     Group attached to the VNIC (Oracle's "Connect public subnet to
     internet" quick action creates one, e.g. `ig-quick-action-NSG`) each
     need ingress rules for TCP 22, 80, and 443 from `0.0.0.0/0`. Both
     layers enforce independently — traffic needs to clear both.
   - **OS-level:** Ubuntu images on OCI also ship with their own `iptables`
     rules that block anything not explicitly allowed, *independently of
     the cloud console rules above* — this trips up nearly everyone on OCI
     specifically. Check with `sudo iptables -L INPUT -n --line-numbers`;
     if there's a catch-all `REJECT` rule, insert ACCEPT rules for 80/443
     *before* it (`sudo iptables -I INPUT <n> -p tcp --dport 80 -j ACCEPT`,
     same for 443), then `sudo netfilter-persistent save` to persist it
     across reboots.

## 2. First-time server setup

SSH in and install Docker:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# log out and back in for the group change to apply
```

Clone the repo and start the stack:

```bash
git clone https://github.com/SidharthJoly/FPLQuant.git
cd FPLQuant
cp .env.example .env
```

Edit `.env` (install an editor first if needed — `sudo apt install -y nano`
— minimized Ubuntu images often don't have one; or just use `sed`) and
uncomment `FPLQUANT_CORS_ALLOWED_ORIGINS`, which already defaults to the
Pages origin:

```bash
sed -i 's/^# *FPLQUANT_CORS_ALLOWED_ORIGINS=/FPLQUANT_CORS_ALLOWED_ORIGINS=/' .env
```

Then:

```bash
docker compose up -d --build
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run fplquant-ingest
curl http://localhost:8000/health   # {"status":"ok"}
```

## 3. HTTPS via DuckDNS + Caddy

1. At [duckdns.org](https://www.duckdns.org), sign in and add a subdomain
   (e.g. `fplquant` → `fplquant.duckdns.org`). **The IP field defaults to
   whatever machine is currently viewing the page — override it to the
   VM's public IP.** Confirm it resolves: `nslookup fplquant.duckdns.org`.
2. Install Caddy on the VM:
   ```bash
   sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
   sudo apt update && sudo apt install -y caddy
   ```
3. Configure it:
   ```bash
   sudo tee /etc/caddy/Caddyfile > /dev/null <<'EOF'
   fplquant.duckdns.org {
       reverse_proxy localhost:8000
   }
   EOF
   sudo systemctl reload caddy
   ```
   Caddy requests and auto-renews a Let's Encrypt cert for the hostname on
   first request — no separate certbot step. Verify:
   ```bash
   curl https://fplquant.duckdns.org/health   # {"status":"ok"}
   ```

If the VM's IP ever changes (instance recreated, etc.), update the IP on
the DuckDNS subdomain's page — the hostname itself doesn't need to change,
so `frontend/config.js` and any bookmarks stay valid.

**Optional hardening, once Caddy is confirmed working:** port 8000 was
opened directly for testing before Caddy was in place. It can be closed
again in the Security List/NSG/iptables (reversing the ingress rules added
for it) since all real traffic now goes through Caddy on 443 — nothing
outside the VM needs to reach 8000 directly anymore.

## 4. Point the frontend at it

`frontend/config.js`:

```js
export const API_BASE = "https://fplquant.duckdns.org";
```

Commit and push — `.github/workflows/pages.yml` redeploys the Pages site
automatically on any push touching `frontend/`.

## 5. Redeploying after changes (CD)

`.github/workflows/deploy.yml` SSHes into the VM and re-pulls/rebuilds —
manually triggered (`workflow_dispatch`), not on every push, so a deploy is
always a deliberate action. Needs these repo secrets set first
(Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | `fplquant.duckdns.org` (or the VM's IP) |
| `DEPLOY_USER` | `ubuntu` |
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

Not wired up yet — worth doing now that the server is actually live and
this is a real (not hypothetical) staleness problem.

## Oracle Always Free: the idle-reclaim gotcha

Oracle reclaims Always Free compute instances that sit idle (CPU, network,
and — for A1/ARM shapes only — memory all under 20% utilization) for a full
7 days straight. For a low-traffic personal project this is a real risk,
not theoretical. Mitigation: a free uptime monitor (e.g. UptimeRobot)
pinging `/health` every few minutes keeps enough baseline traffic to stay
above the threshold. Not set up yet.
