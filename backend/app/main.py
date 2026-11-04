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


# Desktop launcher supplies its bundled frontend; development defaults stay unchanged.
_HERE = os.path.dirname(__file__)
_DIST = os.environ.get("MCU_XREF_FRONTEND_DIR") or os.path.normpath(
    os.path.join(_HERE, "..", "..", "frontend", "dist"))
if not os.path.isdir(_DIST) and not os.environ.get("MCU_XREF_FRONTEND_DIR"):
    _DIST = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "frontend", "dist"))

if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        return FileResponse(os.path.join(_DIST, "index.html"))

    @app.get("/", include_in_schema=False)
    def serve_root():
        return FileResponse(os.path.join(_DIST, "index.html"))
