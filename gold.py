"""GoldPriceService: the ONLY place that talks to the market API.
Swap `fetch_provider` to change provider; everything else reads the DB."""
import requests
from datetime import datetime, timedelta
from models import db, GoldPrice, Alert, Notification
OUNCE_G = 31.1035
KARATS = (24, 21, 18)
POUND_G = 8  # gold pound = 8 g of 21K
state = {"ok": None, "last_ok": None}

def fetch_provider(api_key):
    """Returns 24K EGP per gram. GoldAPI.io (XAU/USD) + open.er-api.com (USD/EGP)."""
    g = requests.get("https://www.goldapi.io/api/XAU/USD", timeout=10,
                     headers={"x-access-token": api_key}).json()
    fx = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10).json()
    return float(g["price"]) / OUNCE_G * float(fx["rates"]["EGP"])

def save_prices(p24, source="api"):
    ts = datetime.utcnow()
    for k in KARATS:
        db.session.add(GoldPrice(karat=k, price_per_gram=round(p24 * k / 24, 2),
                                 source=source, updated_at=ts))
    db.session.commit()
    state.update(ok=True, last_ok=ts)
    check_alerts()

def refresh(api_key):
    """Fetch, store, check alerts. On failure keep last valid price."""
    try:
        save_prices(fetch_provider(api_key))
        return True
    except Exception:
        state["ok"] = False
        return False

def latest(karat):
    rows = (GoldPrice.query.filter_by(karat=karat)
            .order_by(GoldPrice.updated_at.desc()).limit(2).all())
    if not rows: return None
    cur, prev = rows[0], rows[1] if len(rows) > 1 else rows[0]
    ch = cur.price_per_gram - prev.price_per_gram
    return {"karat": karat, "price": cur.price_per_gram, "previous": prev.price_per_gram,
            "change": round(ch, 2),
            "pct": round(ch / prev.price_per_gram * 100, 2) if prev.price_per_gram else 0,
            "updated_at": cur.updated_at.isoformat() + "Z"}

def current_prices():
    out = {str(k): latest(k) for k in KARATS}
    p21 = out["21"]["price"] if out["21"] else None
    return {"karats": out, "api_ok": state["ok"],
            "gold_pound": round(p21 * POUND_G, 2) if p21 else None,
            "ounce_24k": round(out["24"]["price"] * OUNCE_G, 2) if out["24"] else None}

def price_of(karat):
    r = latest(karat)
    return r["price"] if r else None

def history(karat, days):
    since = datetime.utcnow() - timedelta(days=days)
    rows = (GoldPrice.query.filter(GoldPrice.karat == karat, GoldPrice.updated_at >= since)
            .order_by(GoldPrice.updated_at).all())
    pts = [{"t": r.updated_at.isoformat() + "Z", "p": r.price_per_gram} for r in rows]
    v = [r.price_per_gram for r in rows]
    stats = {}
    if v:
        stats = {"high": max(v), "low": min(v), "avg": round(sum(v) / len(v), 2),
                 "current": v[-1], "pct": round((v[-1] - v[0]) / v[0] * 100, 2)}
    return {"points": pts, "stats": stats}

def check_alerts():
    for a in Alert.query.filter_by(status="active").all():
        p = price_of(a.karat)
        if p is None: continue
        if (a.condition == "above" and p >= a.target_price) or \
           (a.condition == "below" and p <= a.target_price):
            a.status = "triggered"
            db.session.add(Notification(user_id=a.user_id, title="Price alert",
                message=f"{a.karat}K gold is {p:,.2f} EGP/g (target {a.target_price:,.2f})."))
    db.session.commit()
