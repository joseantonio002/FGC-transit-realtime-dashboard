"""Simple API to expose collector JSON outputs."""

from __future__ import annotations

import json
import os
import sqlite3
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


def _database_path() -> Path:
  """Return the SQLite database path for analytics endpoints."""
  configured_path: Path = Path(os.getenv("DATABASE_PATH", "database.db"))
  if configured_path.exists():
    return configured_path

  collector_default: Path = _collector_outputs_dir() / "database.db"
  if collector_default.exists():
    return collector_default

  return configured_path


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


def _route_color_by_id() -> dict[str, str]:
  """Build route color lookup from latest vehicles snapshot."""
  route_colors: dict[str, str] = {}
  try:
    vehicles_data: Any = _load_json_file("vehicles.json")
  except HTTPException:
    return route_colors

  for vehicle in vehicles_data.get("vehicles", []):
    route_id: str = str(vehicle.get("route_short_name") or "").strip()
    route_color: str = str(vehicle.get("route_color") or "").strip()
    if route_id and route_color and route_id not in route_colors:
      route_colors[route_id] = route_color

  return route_colors


def _stop_name_by_id() -> dict[str, str]:
  """Build stop name lookup from stops snapshot."""
  stop_names: dict[str, str] = {}
  try:
    stops_data: Any = _load_json_file("stops.json")
  except HTTPException:
    return stop_names

  for stop in stops_data.get("stops", []):
    stop_id: str = str(stop.get("stop_id") or "").strip()
    stop_name: str = str(stop.get("stop_name") or "").strip()
    if stop_id and stop_name:
      stop_names[stop_id] = stop_name

  return stop_names


def _query_top_averages(group_field: str) -> list[sqlite3.Row]:
  """Query top 5 average delays grouped by one table field."""
  db_path: Path = _database_path()
  if not db_path.exists():
    raise HTTPException(status_code=404, detail=f"Database not found: {db_path}")

  allowed_group_fields: set[str] = {"route_id", "stop_id"}
  if group_field not in allowed_group_fields:
    raise HTTPException(status_code=500, detail="Invalid group field")

  query: str = (
    "SELECT "
    f"{group_field} AS grouped_key, "
    "AVG(arrival_delay_total_seconds) AS avg_delay_seconds "
    "FROM historic_delays "
    f"WHERE {group_field} IS NOT NULL AND {group_field} != '' "
    "GROUP BY grouped_key "
    "ORDER BY avg_delay_seconds DESC "
    "LIMIT 5"
  )

  try:
    with sqlite3.connect(db_path) as connection:
      connection.row_factory = sqlite3.Row
      cursor: sqlite3.Cursor = connection.cursor()
      return cursor.execute(query).fetchall()
  except sqlite3.Error as exc:
    raise HTTPException(status_code=500, detail=f"Database query failed: {exc}") from exc


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

@app.get("/arrival_times")
async def get_arrival_times() -> Any:
  """Return JSON content from arrival_times.json."""
  return _load_json_file("arrival_times.json")


@app.get("/top_routes")
async def get_top_routes() -> dict[str, dict[str, Any]]:
  """Return top 5 routes by average delay."""
  rows: list[sqlite3.Row] = _query_top_averages("route_id")
  route_colors: dict[str, str] = _route_color_by_id()

  output: dict[str, dict[str, Any]] = {}
  for index, row in enumerate(rows, start=1):
    route_id: str = str(row["grouped_key"])
    average_delay: int = int(round(float(row["avg_delay_seconds"] or 0)))
    output[str(index)] = {
      "route_name": route_id,
      "delay": average_delay,
      "route_color": route_colors.get(route_id, ""),
    }

  return output


@app.get("/top_stops")
async def get_top_stops() -> dict[str, dict[str, Any]]:
  """Return top 5 stops by average delay."""
  rows: list[sqlite3.Row] = _query_top_averages("stop_id")
  stop_names: dict[str, str] = _stop_name_by_id()

  output: dict[str, dict[str, Any]] = {}
  for index, row in enumerate(rows, start=1):
    stop_id: str = str(row["grouped_key"])
    average_delay: int = int(round(float(row["avg_delay_seconds"] or 0)))
    output[str(index)] = {
      "stop_name": stop_names.get(stop_id, stop_id),
      "delay": average_delay,
    }

  return output
