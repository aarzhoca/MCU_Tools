import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routers import chips, match, st_preview

app = FastAPI(
    title="Nuvoton MCU Cross Reference API",
    description="Find the best-matching Nuvoton MCU for any competitor part number.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chips.router)
app.include_router(match.router)
app.include_router(st_preview.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Serve the built React frontend ────────────────────────────────────────
# Resolves to  <project_root>/frontend/dist  regardless of cwd.
# Works for local (project root) and Docker (/app/backend as cwd)
_HERE = os.path.dirname(__file__)           # backend/app/
_DIST = os.path.normpath(os.path.join(_HERE, "..", "..", "frontend", "dist"))
if not os.path.isdir(_DIST):
    # Docker layout: cwd is /app/backend, dist is at /app/frontend/dist
    _DIST = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "frontend", "dist"))

if os.path.isdir(_DIST):
    # Serve static assets (JS/CSS/images)
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    # Every non-API path returns index.html so React Router works
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        index = os.path.join(_DIST, "index.html")
        return FileResponse(index)

    @app.get("/", include_in_schema=False)
    def serve_root():
        return FileResponse(os.path.join(_DIST, "index.html"))
