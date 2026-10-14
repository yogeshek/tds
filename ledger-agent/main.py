import json
import os
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

LEDGER_BASE = os.environ["LEDGER_BASE"]  # questionData URL with email, quizSign and questionId, without &path=
AIPIPE_TOKEN = os.environ.get("AIPIPE_TOKEN")
CHAT_URL = os.environ.get("CHAT_URL", "https://aipipe.org/openai/v1/chat/completions")
MODEL = os.environ.get("MODEL", "gpt-4.1-mini")

IST = timezone(timedelta(hours=5, minutes=30))  # API notes: business dates use Asia/Kolkata
HEADERS = {"User-Agent": "Mozilla/5.0 ledger-agent"}  # Cloudflare 403s the default python UA

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA = {"orders": [], "values": {}, "loaded_at": 0}
LOCK = threading.Lock()


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_data():
    rates = requests.get(LEDGER_BASE + "&path=%2Frates", headers=HEADERS, timeout=30).json()["usd_per_unit"]
    text = requests.get(LEDGER_BASE + "&path=%2Fexport", headers=HEADERS, timeout=60).text
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]

    # An id can appear more than once; the row with the latest updated_at is current
    latest = {}
    for r in rows:
        r["_updated"] = parse_ts(r["updated_at"])
        if r["id"] not in latest or r["_updated"] > latest[r["id"]]["_updated"]:
            latest[r["id"]] = r

    orders = []
    for r in latest.values():
        created = parse_ts(r["created_at"]).astimezone(IST)
        r["date"] = created.date().isoformat()
        r["month"] = created.strftime("%Y-%m")
        r["usd"] = r["amount"] * rates[r["currency"]]
        orders.append(r)

    values = {f: sorted({o[f] for o in orders}) for f in ("region", "product", "currency", "status")}
    values["date_range"] = [min(o["date"] for o in orders), max(o["date"] for o in orders)]
    with LOCK:
        DATA.update(orders=orders, values=values, loaded_at=time.time())
    print(f"Loaded {len(rows)} rows -> {len(orders)} current orders")


def ensure_data():
    if not DATA["orders"] or time.time() - DATA["loaded_at"] > 3600:
        load_data()


@app.on_event("startup")
def startup():
    ensure_data()


SYSTEM_PROMPT = """You convert questions about an appliance order ledger into a JSON query plan.

Each order has: id, customer (like "C1120"), region, product, qty, amount (converted to USD for you),
status, and a business date (Asia/Kolkata). Valid values:
{values}

Return ONLY a JSON object with these keys:
- "metric": one of
    "revenue"          total USD amount (paid orders)
    "refund_amount"    total USD amount of refunded orders
    "order_count"      number of orders
    "units"            total qty sold (paid orders)
    "customer_count"   number of distinct customers
    "avg_order_value"  average USD amount per order (paid orders)
- "status": "paid", "refunded", "void" or "any". Use null unless the question names a status explicitly
  (e.g. "how many refunded orders" -> "refunded", "how many orders were voided" -> "void").
- "filters": object with optional keys
    "region": [list], "product": [list], "customer": [list], "currency": [list of original currencies],
    "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD"   (inclusive; "March 2026" -> 2026-03-01..2026-03-31,
    "Q1 2026" -> 2026-01-01..2026-03-31, "first half of 2026" -> 2026-01-01..2026-06-30)
  Use the exact spellings from the valid values. Omit filters the question does not mention.
- "group_by": null, or one of "product", "region", "customer", "month", "currency"
  when the question asks "which ..." / "top ..." / "best ..." / "lowest ...".
- "order": "desc" (highest/most/top/best) or "asc" (lowest/least/worst). Default "desc".
- "answer": what to return when group_by is set:
    "name"    the name of the top group (e.g. "Which product had the most revenue?")
    "value"   the metric value of the top group (e.g. "What was the revenue of the best-selling product?")
    "names"   a ranked list of the top "limit" names (e.g. "Top 3 customers by revenue")
- "limit": integer, number of groups for "names" (default 1).
"""


def make_plan(question):
    prompt = SYSTEM_PROMPT.format(values=json.dumps(DATA["values"]))
    last_err = None
    for _ in range(2):
        try:
            r = requests.post(
                CHAT_URL,
                headers={"Authorization": f"Bearer {AIPIPE_TOKEN}"},
                json={
                    "model": MODEL,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": question},
                    ],
                },
                timeout=10,
            )
            r.raise_for_status()
            return json.loads(r.json()["choices"][0]["message"]["content"])
        except Exception as e:
            last_err = e
    raise RuntimeError(f"LLM planning failed: {last_err}")


DEFAULT_STATUS = {
    "revenue": "paid",
    "units": "paid",
    "avg_order_value": "paid",
    "customer_count": "paid",
    "refund_amount": "refunded",
    "order_count": "any",
}


def canon(field, wanted):
    # Map LLM spellings onto the API's exact spellings, case-insensitively
    if field == "customer":
        return {w.strip().upper() for w in wanted}
    lookup = {v.lower(): v for v in DATA["values"][field]}
    return {lookup.get(w.strip().lower(), w) for w in wanted}


def compute(metric, rows):
    if metric in ("revenue", "refund_amount"):
        return round(sum(o["usd"] for o in rows) + 1e-9, 2)
    if metric == "avg_order_value":
        return round(sum(o["usd"] for o in rows) / len(rows) + 1e-9, 2) if rows else 0
    if metric == "units":
        return sum(o["qty"] for o in rows)
    if metric == "customer_count":
        return len({o["customer"] for o in rows})
    return len(rows)


def run_plan(plan):
    metric = plan.get("metric") or "revenue"
    status = plan.get("status") or DEFAULT_STATUS.get(metric, "any")
    f = plan.get("filters") or {}

    rows = DATA["orders"]
    if status != "any":
        rows = [o for o in rows if o["status"] == status]
    for field in ("region", "product", "customer", "currency"):
        if f.get(field):
            allowed = canon(field, f[field])
            rows = [o for o in rows if o[field] in allowed]
    if f.get("date_from"):
        rows = [o for o in rows if o["date"] >= f["date_from"]]
    if f.get("date_to"):
        rows = [o for o in rows if o["date"] <= f["date_to"]]

    group_by = plan.get("group_by")
    if not group_by:
        return compute(metric, rows)

    groups = defaultdict(list)
    for o in rows:
        groups[o[group_by]].append(o)
    ranked = sorted(
        ((k, compute(metric, v)) for k, v in groups.items()),
        key=lambda kv: (-kv[1], kv[0]) if plan.get("order", "desc") == "desc" else (kv[1], kv[0]),
    )
    if not ranked:
        return None
    answer = plan.get("answer", "name")
    if answer == "value":
        return ranked[0][1]
    if answer == "names":
        return [k for k, _ in ranked[: int(plan.get("limit") or 1)]]
    return ranked[0][0]


@app.post("/")
@app.post("/ask")
async def ask(request: Request):
    body = await request.json()
    question = body.get("question", "")
    ensure_data()
    plan = make_plan(question)
    answer = run_plan(plan)
    print(json.dumps({"question": question, "plan": plan, "answer": answer}))
    return {"answer": answer}


@app.get("/health")
def health():
    return {"status": "ok", "orders": len(DATA["orders"])}
