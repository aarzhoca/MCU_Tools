# Nuvoton MCU Cross Reference — Deployment Guide

## Quick summary

The app is a single Python process (FastAPI) that serves both the REST API
and the React frontend. After build, only **one server** needs to run.

---

## Option A — Run locally (Windows, no install needed)

Double-click **`start.bat`**.

- Builds the frontend on first run (requires Node.js installed once)
- Starts the server at http://localhost:8000
- Opens the browser automatically
- Subsequent runs skip the build step (uses cached `frontend/dist/`)

To rebuild the frontend after a UI change: delete `frontend/dist/` then re-run `start.bat`.

---

## Option B — Docker (recommended for IT / server deployment)

### Prerequisites
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)

### Build and run

```bash
# From the project root folder:
docker compose up --build
```

The app is available at **http://localhost:8000** (or your server IP).

To run in background:
```bash
docker compose up -d --build
```

To stop:
```bash
docker compose down
```

### Data persistence

The competitor and Nuvoton catalog JSON files are mounted as a volume:
```
./backend/data  →  /app/backend/data  (inside container)
```
Catalog changes (via the Import UI) survive container restarts automatically.

---

## Option C — Cloud hosting recommendations

### For an internal sales tool (behind Nuvoton VPN)

| Option | Cost | Effort | Notes |
|---|---|---|---|
| **Azure App Service** | ~$15/mo (B1) | Low | Best fit if Nuvoton uses Azure AD; easy SSL, custom domain |
| **AWS ECS Fargate** | ~$12/mo | Medium | Good if Nuvoton uses AWS; pay-per-use |
| **Nuvoton on-premise server** | $0 extra | Low | IT runs `docker compose up -d`; most control |

### For public access (linked from nuvoton.com)

| Option | Cost | Effort | Notes |
|---|---|---|---|
| **Azure App Service + Azure Front Door** | ~$30/mo | Low | Enterprise-grade, SSL, CDN built-in |
| **Google Cloud Run** | Pay-per-request (~$0 idle) | Low | Auto-scales to zero; easy `gcloud run deploy` |
| **Render.com** | Free tier / $7/mo | Very low | `render.yaml` included below; Git-push deploy |

---

## Deploying to Azure App Service (recommended for Nuvoton IT)

```bash
# 1. Build and push the Docker image to Azure Container Registry
az acr build --registry <your-acr-name> --image nuvoton-xref:latest .

# 2. Create the App Service
az webapp create \
  --resource-group <rg> \
  --plan <plan> \
  --name nuvoton-mcu-xref \
  --deployment-container-image-name <your-acr-name>.azurecr.io/nuvoton-xref:latest

# 3. Set the port
az webapp config appsettings set \
  --name nuvoton-mcu-xref \
  --resource-group <rg> \
  --settings WEBSITES_PORT=8000
```

The tool will be live at: `https://nuvoton-mcu-xref.azurewebsites.net`

---

## Deploying to Render.com (fastest zero-config option)

Create a file `render.yaml` at the project root (already included) and connect
the GitHub repository at https://render.com. Render auto-builds and deploys on
every git push.

---

## Linking from nuvoton.com/tool-and-software/software-tool/

Once hosted, send the IT department:

1. The live URL (e.g. `https://nuvoton-mcu-xref.azurewebsites.net`)
2. A short description: *"Nuvoton MCU Cross Reference Tool — enter any competitor MCU
   part number and get the best-matching Nuvoton part with a parameter-by-parameter
   comparison table."*
3. Request a listing under the **Software Tool** category on the tools page.

If IT prefers to self-host on their servers, hand them:
- This repository (or a ZIP of the project folder)
- These instructions (this file)
- Command to run: `docker compose up -d --build`

---

## Environment variables (optional)

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | Override the listening port |
| `DATA_DIR` | `backend/data` | Override catalog storage path |

---

## Health check endpoint

`GET /health` returns `{"status": "ok"}` — use this for uptime monitors and
load-balancer health checks.
