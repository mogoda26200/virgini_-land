# GoldTrack
Egyptian gold price tracker, calculators, portfolio, history, alerts and admin panel (Flask + SQLAlchemy + vanilla JS + Chart.js).

## How the price system works
`services/gold.py` (GoldPriceService) is the only code that calls the market API. It fetches XAU/USD from GoldAPI.io and USD/EGP from open.er-api.com, converts the ounce to a 24K gram price (÷31.1035 × EGP rate), derives 21K (×21/24) and 18K (×18/24), and stores each fetch in `gold_price`. Every page, calculator, portfolio valuation, chart and alert reads from that table, so a new price updates everything. Gold pound = 8 g of 21K. To change provider, edit `fetch_provider()` only.
If the API fails, the last valid price stays, the UI shows "feed unavailable", and the site keeps working. Admins can enter a 24K price manually.

## Scheduled updates
APScheduler runs `scheduled()` every `UPDATE_MINUTES` (default 5): fetch → save 24/21/18K → compare with previous → check active alerts → create notifications.

## Setup
1. `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
2. `cp .env.example .env`, set `SECRET_KEY` and `GOLD_API_KEY` (free key at goldapi.io).
3. Database: SQLite works immediately. For PostgreSQL: `createdb goldtrack` and set `DATABASE_URL=postgresql://user:pass@localhost/goldtrack`. Tables are created on first start.
4. Run: `python app.py` → http://localhost:5000 (frontend is served by Flask from `templates/` and `static/`).
5. Admin: register normally, or run `flask --app app create-admin`; open `#admin`.

## Not yet included
Forgot-password email, profile picture upload, CSV/PDF export, USD/ounce display switch, portfolio edit/search, admin user deletion, admin_logs/transactions tables, and the notification-for-portfolio-change messages. Passwords are hashed, sessions are HttpOnly cookies, inputs are validated, SQL uses the ORM, and secrets live in `.env`.
