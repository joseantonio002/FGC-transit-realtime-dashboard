"""Simple API to expose collector JSON outputs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


def _collector_outputs_dir() -> Path:
  """Return the directory where collector JSON files are stored."""
  return Path(os.getenv("COLLECTOR_OUTPUTS_DIR", "/collector_outputs"))


def _cors_allow_origins() -> list[str]:
  """Return the configured CORS allow origins list."""
  raw_origins: str = os.getenv("CORS_ALLOW_ORIGINS", "*")
  origins: list[str] = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
  if not origins:
    return ["*"]
  return origins


def _load_json_file(file_name: str) -> Any:
  """Read and decode a JSON file from the collector outputs directory."""
  file_path: Path = _collector_outputs_dir() / file_name

  if not file_path.exists():
    raise HTTPException(status_code=404, detail=f"File not found: {file_name}")

  try:
    with file_path.open("r", encoding="utf-8") as file:
      return json.load(file)
  except json.JSONDecodeError as exc:
    raise HTTPException(
      status_code=500,
      detail=f"Invalid JSON in file: {file_name}",
    ) from exc
  except OSError as exc:
    raise HTTPException(
      status_code=500,
      detail=f"Unable to read file: {file_name}",
    ) from exc


app: FastAPI = FastAPI(title="Collector Outputs API", version="0.1.0")

app.add_middleware(
  CORSMiddleware,
  allow_origins=_cors_allow_origins(),
  allow_credentials=False,
  allow_methods=["GET"],
  allow_headers=["*"],
)


@app.get("/shapes")
async def get_shapes() -> Any:
  """Return JSON content from shapes.json."""
  return _load_json_file("shapes.json")


@app.get("/stops")
async def get_stops() -> Any:
  """Return JSON content from stops.json."""
  return _load_json_file("stops.json")


@app.get("/vehicles")
async def get_vehicles() -> Any:
  """Return JSON content from vehicles.json."""
  return _load_json_file("vehicles.json")
