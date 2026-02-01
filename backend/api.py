"""Sales Dashboard Prototype API

Run locally:
  cd backend
  pip install -r requirements.txt
  python api.py
  # API runs on http://localhost:5000

Recommended (uses the repo virtualenv at .venv/):
  source ../.venv/bin/activate
  cd backend
  pip install -r requirements.txt
  python api.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS


APP_ROOT = Path(__file__).resolve().parent
DATA_PATH = APP_ROOT / "data" / "sales.csv"


def load_sales_df() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing data file: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    expected = {"Quarter", "Store", "Sales"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(missing)}")

    df = df[["Quarter", "Store", "Sales"]].copy()
    df["Quarter"] = df["Quarter"].astype(str).str.strip()
    df["Store"] = df["Store"].astype(str).str.strip()
    df["Sales"] = pd.to_numeric(df["Sales"], errors="coerce")
    df = df.dropna(subset=["Quarter", "Store", "Sales"])
    df["Sales"] = df["Sales"].astype(int)

    return df


app = Flask(__name__)
CORS(app)


@app.get("/api/stores")
def get_stores():
    print("[api] GET /api/stores")
    try:
        df = load_sales_df()
        stores = sorted(df["Store"].unique().tolist())
        return jsonify({"stores": stores})
    except Exception as e:
        print(f"[api] ERROR /api/stores: {e}")
        return jsonify({"error": "Failed to load stores", "detail": str(e)}), 500


@app.get("/api/sales")
def get_sales():
    store = (request.args.get("store") or "").strip()
    print(f"[api] GET /api/sales?store={store!r}")

    if not store:
        return (
            jsonify({"error": "Missing required query param", "param": "store"}),
            400,
        )

    try:
        df = load_sales_df()
        filtered = df[df["Store"] == store].copy()

        if filtered.empty:
            known = sorted(df["Store"].unique().tolist())
            return (
                jsonify(
                    {
                        "error": "Unknown store",
                        "store": store,
                        "knownStores": known,
                    }
                ),
                404,
            )

        rows = (
            filtered[["Quarter", "Store", "Sales"]]
            .rename(columns={"Quarter": "quarter", "Store": "store", "Sales": "sales"})
            .to_dict(orient="records")
        )

        return jsonify({"store": store, "data": rows})
    except Exception as e:
        print(f"[api] ERROR /api/sales: {e}")
        return jsonify({"error": "Failed to load sales data", "detail": str(e)}), 500


if __name__ == "__main__":
    # Debug on for a friendlier prototype dev loop.
    app.run(host="127.0.0.1", port=5000, debug=True)
