# Meal Planner

A web application for recipe management, weekly meal planning, and grocery list generation.

## Features

- **Recipe Scraping**: Import recipes from Ambitious Kitchen and Smitten Kitchen
- **Recipe Box**: Save your favorite recipes
- **Weekly Planner**: Assign recipes to days of the week
- **Smart Grocery List**: Automatically aggregates ingredients across recipes

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, SQLite
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Recipe Scraping**: BeautifulSoup for JSON-LD extraction

## Getting Started

### Quick Start (Recommended)

```bash
# Run everything with one command
./run.sh
```

This will:
- Install Python and Node dependencies (first run only)
- Start both backend and frontend servers

Then open http://localhost:5173

### Other Commands

```bash
./run.sh setup      # Install dependencies only
./run.sh backend    # Start only the backend
./run.sh frontend   # Start only the frontend
```

### Manual Setup

If you prefer to run things manually:

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Supported Recipe Sites

- [Ambitious Kitchen](https://www.ambitiouskitchen.com/)
- [Smitten Kitchen](https://smittenkitchen.com/)

Other sites may work if they include JSON-LD structured recipe data.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/recipes/scrape` | POST | Scrape recipe from URL |
| `/api/recipes` | GET | List all saved recipes |
| `/api/recipes/{id}` | GET/DELETE | Get or delete recipe |
| `/api/recipes/{id}/add-to-box` | POST | Add to recipe box |
| `/api/recipes/box/all` | GET | Get recipe box contents |
| `/api/meal-plans` | GET/POST | Manage weekly meal plans |
| `/api/grocery-list` | POST | Generate aggregated grocery list |

## Project Structure

```
hack_day_project/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── database.py       # SQLAlchemy setup
│   │   ├── models.py         # Database models
│   │   ├── routers/          # API endpoints
│   │   └── services/         # Business logic
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/       # React components
│       └── api/              # API client
└── README.md
```
