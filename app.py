from datetime import datetime, date
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from config import Config
from models import db, User, Holding, Alert, Notification, GoldPrice
from services import gold

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)
db.init_app(app)
lm = LoginManager(app)

@lm.user_loader
def load(uid): return db.session.get(User, int(uid))
@lm.unauthorized_handler
def unauth(): return jsonify(error="Please log in."), 401

def err(msg, code=400): return jsonify(error=msg), code
def num(v, name, minimum=0.0001):
    try: x = float(v)
    except (TypeError, ValueError): raise ValueError(f"{name} must be a number.")
    if x < minimum: raise ValueError(f"{name} must be greater than 0.")
    return x
def karat_of(v):
    if int(v) not in gold.KARATS: raise ValueError("Karat must be 24, 21 or 18.")
    return int(v)

@app.errorhandler(ValueError)
def bad(e): return err(str(e))
@app.errorhandler(Exception)
def fail(e):
    app.logger.exception(e); return err("Something went wrong. Please try again.", 500)

@app.get("/")
def index(): return render_template("index.html")

# ---------- prices ----------
@app.get("/api/prices")
def prices(): return jsonify(gold.current_prices())

@app.post("/api/prices/refresh")
def refresh_now():
    ok = gold.refresh(Config.GOLD_API_KEY)
    return jsonify(ok=ok, **gold.current_prices())

@app.get("/api/history")
def history():
    return jsonify(gold.history(karat_of(request.args.get("karat", 21)),
                                int(request.args.get("days", 7))))

@app.get("/api/analysis")
def analysis():
    k = karat_of(request.args.get("karat", 21))
    out = {f"d{d}": gold.history(k, d)["stats"] for d in (1, 7, 30)}
    m = out["d30"]
    if m:
        out["vs_avg_pct"] = round((m["current"] - m["avg"]) / m["avg"] * 100, 2)
        out["volatility_pct"] = round((m["high"] - m["low"]) / m["avg"] * 100, 2)
    return jsonify(out)

# ---------- calculators (all use the central price) ----------
@app.post("/api/calc/<kind>")
def calc(kind):
    d = request.json or {}
    k = karat_of(d.get("karat", 21))
    p = gold.price_of(k)
    if p is None: return err("Live price unavailable right now.", 503)
    mk = float(d.get("making_pct") or 0) / 100
    if kind == "value":
        w = num(d.get("weight"), "Weight"); v = w * p
        mc = v * mk + float(d.get("fees") or 0)
        return jsonify(price=p, weight=w, value=round(v, 2), making=round(mc, 2), total=round(v + mc, 2))
    if kind == "budget":
        b = num(d.get("budget"), "Budget")
        return jsonify(price=p, grams_before=round(b / p, 2), grams_after=round(b / (p * (1 + mk)), 2))
    if kind == "profit":
        w = num(d.get("weight"), "Weight"); bp = num(d.get("buy_price"), "Purchase price")
        inv = w * bp + float(d.get("fees") or 0); cur = w * p
        return jsonify(investment=round(inv, 2), current=round(cur, 2),
                       profit=round(cur - inv, 2), pct=round((cur - inv) / inv * 100, 2))
    return err("Unknown calculator.", 404)

# ---------- auth ----------
@app.post("/api/register")
def register():
    d = request.json or {}
    email = (d.get("email") or "").strip().lower()
    if "@" not in email or len(d.get("password") or "") < 8 or not d.get("name"):
        return err("Enter a name, a valid email and a password of 8+ characters.")
    if User.query.filter_by(email=email).first(): return err("Email already registered.")
    u = User(name=d["name"][:80], email=email, password_hash=generate_password_hash(d["password"]))
    db.session.add(u); db.session.commit(); login_user(u)
    return jsonify(id=u.id, name=u.name)

@app.post("/api/login")
def login():
    d = request.json or {}
    u = User.query.filter_by(email=(d.get("email") or "").lower()).first()
    if not u or not check_password_hash(u.password_hash, d.get("password") or ""):
        return err("Wrong email or password.", 401)
    if not u.is_active_user: return err("This account is disabled.", 403)
    login_user(u); return jsonify(id=u.id, name=u.name, is_admin=u.is_admin)

@app.post("/api/logout")
def logout(): logout_user(); return jsonify(ok=True)

@app.get("/api/me")
def me():
    if not current_user.is_authenticated: return jsonify(user=None)
    return jsonify(user=dict(id=current_user.id, name=current_user.name, is_admin=current_user.is_admin))

# ---------- portfolio ----------
def hold_json(h, prices):
    cur = h.weight * prices[h.karat]; inv = h.weight * h.purchase_price + (h.fees or 0)
    return dict(id=h.id, karat=h.karat, weight=h.weight, purchase_price=h.purchase_price,
                date=str(h.purchase_date), fees=h.fees, value=round(cur, 2),
                investment=round(inv, 2), profit=round(cur - inv, 2))

@app.get("/api/portfolio")
@login_required
def portfolio():
    pr = {k: gold.price_of(k) or 0 for k in gold.KARATS}
    items = [hold_json(h, pr) for h in Holding.query.filter_by(user_id=current_user.id)]
    inv = sum(i["investment"] for i in items); val = sum(i["value"] for i in items)
    return jsonify(items=items, total_value=round(val, 2), total_investment=round(inv, 2),
                   profit=round(val - inv, 2), pct=round((val - inv) / inv * 100, 2) if inv else 0,
                   grams=round(sum(i["weight"] for i in items), 2))

@app.post("/api/portfolio")
@login_required
def add_holding():
    d = request.json or {}
    h = Holding(user_id=current_user.id, karat=karat_of(d.get("karat")),
                weight=num(d.get("weight"), "Weight"), purchase_price=num(d.get("purchase_price"), "Price"),
                purchase_date=date.fromisoformat(d.get("date") or str(date.today())),
                fees=float(d.get("fees") or 0))
    db.session.add(h); db.session.commit(); return jsonify(id=h.id)

@app.delete("/api/portfolio/<int:i>")
@login_required
def del_holding(i):
    h = Holding.query.filter_by(id=i, user_id=current_user.id).first_or_404()
    db.session.delete(h); db.session.commit(); return jsonify(ok=True)

# ---------- alerts & notifications ----------
@app.route("/api/alerts", methods=["GET", "POST"])
@login_required
def alerts():
    if request.method == "POST":
        d = request.json or {}
        if d.get("condition") not in ("above", "below"): return err("Choose above or below.")
        db.session.add(Alert(user_id=current_user.id, karat=karat_of(d.get("karat")),
                             target_price=num(d.get("target"), "Target price"), condition=d["condition"]))
        db.session.commit()
    return jsonify([dict(id=a.id, karat=a.karat, target=a.target_price, condition=a.condition,
                         status=a.status) for a in Alert.query.filter_by(user_id=current_user.id)])

@app.route("/api/alerts/<int:i>", methods=["DELETE", "PATCH"])
@login_required
def alert_one(i):
    a = Alert.query.filter_by(id=i, user_id=current_user.id).first_or_404()
    if request.method == "DELETE": db.session.delete(a)
    else: a.status = "disabled" if a.status == "active" else "active"
    db.session.commit(); return jsonify(ok=True)

@app.get("/api/notifications")
@login_required
def notifs():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.id.desc()).limit(30)
    return jsonify([dict(title=n.title, message=n.message, at=n.created_at.isoformat() + "Z") for n in rows])

# ---------- admin ----------
def admin_only():
    return current_user.is_authenticated and current_user.is_admin

@app.get("/api/admin/stats")
def admin_stats():
    if not admin_only(): return err("Admins only.", 403)
    return jsonify(users=User.query.count(), holdings=Holding.query.count(),
                   alerts=Alert.query.count(), api_ok=gold.state["ok"],
                   last_ok=str(gold.state["last_ok"]),
                   user_list=[dict(id=u.id, name=u.name, email=u.email, active=u.is_active_user) for u in User.query.limit(100)])

@app.post("/api/admin/prices")  # manual fallback when the API is down
def admin_prices():
    if not admin_only(): return err("Admins only.", 403)
    gold.save_prices(num((request.json or {}).get("price_24k"), "24K price"), source="manual")
    return jsonify(ok=True)

@app.post("/api/admin/users/<int:i>/toggle")
def admin_toggle(i):
    if not admin_only(): return err("Admins only.", 403)
    u = db.get_or_404(User, i); u.is_active_user = not u.is_active_user
    db.session.commit(); return jsonify(ok=True)

def scheduled():
    with app.app_context(): gold.refresh(Config.GOLD_API_KEY)

@app.cli.command("create-admin")
def create_admin():
    import click
    email = click.prompt("Admin email"); pw = click.prompt("Password", hide_input=True)
    db.session.add(User(name="Admin", email=email.lower(), is_admin=True,
                        password_hash=generate_password_hash(pw)))
    db.session.commit(); print("Admin created.")

with app.app_context(): db.create_all()
if __name__ == "__main__":
    s = BackgroundScheduler(); s.add_job(scheduled, "interval", minutes=Config.UPDATE_MINUTES,
                                          next_run_time=datetime.now()); s.start()
    app.run(debug=False, use_reloader=False)
