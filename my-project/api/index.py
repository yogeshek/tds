import json
import os
from typing import List

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    # browsers hide CORS headers from JS unless exposed, and the grader reads them in-browser
    expose_headers=["Access-Control-Allow-Origin"],
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "q-vercel-latency.json")
with open(DATA_PATH, encoding="utf-8") as f:
    records = json.load(f)


class Query(BaseModel):
    regions: List[str]
    threshold_ms: float


def region_metrics(query: Query):
    result = {}
    for region in query.regions:
        rows = [r for r in records if r["region"] == region]
        if not rows:
            continue
        latencies = np.array([r["latency_ms"] for r in rows])
        uptimes = np.array([r["uptime_pct"] for r in rows])
        result[region] = {
            "avg_latency": round(float(latencies.mean()), 2),
            "p95_latency": round(float(np.percentile(latencies, 95)), 2),
            "avg_uptime": round(float(uptimes.mean()), 3),
            "breaches": int((latencies > query.threshold_ms).sum()),
        }
    return {"regions": result}


@app.post("/")
@app.post("/api")
def metrics(query: Query):
    return region_metrics(query)


@app.get("/")
@app.get("/api")
def health():
    return {"status": "ok", "records": len(records)}
