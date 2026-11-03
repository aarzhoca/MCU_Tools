# Nuvoton MCU Cross Reference Tool

A web-based dashboard for Nuvoton sales reps to quickly find the best-matching Nuvoton MCU for any competitor part.

## Features

- Enter a competitor chip part number (STM32, ESP32, PIC, AVR, LPC, Renesas, etc.)
- Select up to **5 key parameters** to prioritize (CPU freq, RAM, Flash, GPIO, ADC, peripherals...)
- KNN similarity algorithm ranks all Nuvoton parts by weighted parameter match
- Comparison table with per-parameter similarity bars and deltas
- Top 5 ranked Nuvoton alternatives

## Project Structure

```
Cross_Ref_Dashboard/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── main.py             # FastAPI application entry point
│   │   ├── models.py           # Pydantic data models
│   │   ├── matcher.py          # KNN matching algorithm
│   │   ├── data_loader.py      # JSON catalog loading
│   │   └── routers/
│   │       ├── chips.py        # GET /api/chips/* endpoints
│   │       └── match.py        # POST /api/match endpoint
│   ├── data/
│   │   ├── nuvoton_parts.json  # Nuvoton MCU catalog
│   │   └── competitor_parts.json  # Competitor MCU catalog
│   ├── scripts/
│   │   └── import_xls.py       # One-time XLS import from Nuvoton datasheets
│   └── requirements.txt
├── frontend/                   # React + TypeScript + Vite frontend
│   ├── src/
│   │   ├── App.tsx             # Main layout + state
│   │   ├── api.ts              # API client functions
│   │   ├── types.ts            # TypeScript interfaces
│   │   └── components/
│   │       ├── SearchPanel.tsx       # Input form + parameter selection
│   │       ├── ResultsPanel.tsx      # Results display
│   │       ├── ComparisonTable.tsx   # Parameter comparison table
│   │       └── TopMatches.tsx        # Top-N match cards
│   └── package.json
├── Nuvoton mcu datasheet/      # Source XLS parametric sheets
├── reference/                  # Reference documents
├── .vscode/                    # VS Code workspace settings + launch configs
└── README.md
```

## Quick Start

### Prerequisites

- **Python 3.12** (recommended: 3.12.10, the last 3.12 release with a Windows installer —
  3.12.11+ is security-only and source-only, no installer available).
  Newer versions (3.13+) are not supported yet — `numpy==2.1.1` and `scikit-learn==1.5.2`
  have no prebuilt Windows wheels for them, so `pip install` tries to compile from source
  and fails unless a C/C++ compiler is installed. Use the `py` launcher to select 3.12
  even if a newer Python is also installed (`py -3.12 -m venv .venv`).
  (The Docker image pins Python 3.11 instead — that's a separate, self-contained build
  environment and doesn't need to match your local interpreter.)
- Node.js 18+ for the frontend.

### 1. Backend setup

```bash
cd backend

# Create virtual environment (Windows) - use Python 3.12 explicitly
py -3.12 -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 2. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: http://localhost:5173

### 3. Import real Nuvoton data from XLS (optional)

The backend ships with a hand-curated `nuvoton_parts.json`. To replace it with
data parsed directly from the Nuvoton parametric XLS files:

```bash
cd backend
python scripts/import_xls.py
```

This reads all `.xls` files from `Nuvoton mcu datasheet/`, unifies the column
headers, and writes a new `backend/data/nuvoton_parts.json`.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/characteristics` | List all available comparison parameters |
| GET | `/api/chips/nuvoton` | List all Nuvoton parts |
| GET | `/api/chips/competitor` | List all competitor parts |
| GET | `/api/chips/competitor/search?q=STM32` | Search competitor parts |
| GET | `/api/chips/competitor/{part}` | Get single competitor part |
| POST | `/api/match` | Find best Nuvoton matches |

### POST /api/match

```json
{
  "part_number": "STM32F103C8",
  "characteristics": ["cpu_freq_mhz", "ram_kb", "flash_kb", "gpio", "usb"],
  "top_k": 5
}
```

## Adding More Competitor Parts

Edit `backend/data/competitor_parts.json`. Each entry must include all fields
from the schema in `backend/app/models.py`.

## Matching Algorithm

1. For each selected parameter, compute min/max across the full Nuvoton catalog
2. Normalize competitor and Nuvoton values to \[0, 1\]
3. Compute root-mean-square distance in the normalized feature space
4. Score = 1 / (1 + RMSE) × 100 — higher is better
5. Return top K Nuvoton parts by score

## Reference Documents

- `Nuvoton AI Cross Referencing Tool for MCUs.pdf` — Extended spec document
- `nuvoton_chip_matcher_ui.html` — Original demo prototype UI
- `cross reference design.png` — UI design reference
