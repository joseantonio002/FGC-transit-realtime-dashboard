import csv
import json
from pathlib import Path
from typing import Any
import io


BASE_GTFS_SCHEDULED_PATH: Path = (Path(__file__).resolve().parent / "./GTFS-Scheduled-data").resolve()
ROUTES_PATH: Path = BASE_GTFS_SCHEDULED_PATH / "routes.txt"
TRIPS_PATH: Path = BASE_GTFS_SCHEDULED_PATH / "trips.txt"
STOP_TIMES_PATH: Path = BASE_GTFS_SCHEDULED_PATH / "stop_times.txt"


def load_routes_by_id() -> dict[str, dict[str, str]]:
  """Read routes.txt and index rows by route_id."""
  routes_by_id: dict[str, dict[str, str]] = {}

  with open(ROUTES_PATH, "r", encoding="utf-8") as routes_file:
    reader: csv.DictReader[str] = csv.DictReader(routes_file)
    for row in reader:
      route_id: str = (row.get("route_id") or "").strip()
      if not route_id:
        continue

      route_data: dict[str, str] = {}
      for key, value in row.items():
        if key == "route_id":
          continue
        route_data[key] = value or ""

      routes_by_id[route_id] = route_data

  return routes_by_id


def load_trips_by_id() -> dict[str, dict[str, str]]:
  """Read trips.txt and index rows by trip_id."""
  trips_by_id: dict[str, dict[str, str]] = {}

  with open(TRIPS_PATH, "r", encoding="utf-8") as trips_file:
    reader: csv.DictReader[str] = csv.DictReader(trips_file)
    for row in reader:
      trip_id: str = (row.get("trip_id") or "").strip()
      if not trip_id:
        continue

      trip_data: dict[str, str] = {}
      for key, value in row.items():
        if key == "trip_id":
          continue
        trip_data[key] = value or ""

      trips_by_id[trip_id] = trip_data

  return trips_by_id


def load_stop_times_by_trip() -> dict[str, dict[str, dict[str, str]]]:
  """Read stop_times.txt and group by trip_id with stop_id as nested key."""
  stop_times_by_trip: dict[str, dict[str, dict[str, str]]] = {}

  with open(STOP_TIMES_PATH, "r", encoding="utf-8") as stop_times_file:
    reader: csv.DictReader[str] = csv.DictReader(stop_times_file)
    for row in reader:
      trip_id: str = (row.get("trip_id") or "").strip()
      stop_id: str = (row.get("stop_id") or "").strip()
      if not trip_id or not stop_id:
        continue

      if trip_id not in stop_times_by_trip:
        stop_times_by_trip[trip_id] = {}

      stop_times_by_trip[trip_id][stop_id] = {
        "arrival_time": row.get("arrival_time") or "",
        "departure_time": row.get("departure_time") or "",
        "stop_sequence": row.get("stop_sequence") or "",
      }

  return stop_times_by_trip


def stops_to_json(stops: str) -> dict[str, list[dict[str, Any]]]:
  """Convert stops.txt content into one JSON entry per station stop."""
  reader: csv.DictReader[str] = csv.DictReader(io.StringIO(stops))
  stations_by_id: dict[str, dict[str, Any]] = {}
  station_order: list[str] = []

  for row in reader:
    stop_id: str = (row.get("stop_id") or "").strip()
    parent_station: str = (row.get("parent_station") or "").strip()
    canonical_stop_id: str = parent_station or stop_id

    if not canonical_stop_id:
      continue

    if canonical_stop_id not in stations_by_id:
      stations_by_id[canonical_stop_id] = {
        "stop_id": canonical_stop_id,
        "stop_name": row.get("stop_name"),
        "stop_lon": row.get("stop_lon"),
        "stop_lat": row.get("stop_lat"),
        "other_ids": [],
      }

      station_order.append(canonical_stop_id)

    if parent_station and stop_id and stop_id != canonical_stop_id:
      other_ids: list[str] = stations_by_id[canonical_stop_id]["other_ids"]
      if stop_id not in other_ids:
        other_ids.append(stop_id)

  unique_stops: list[dict[str, Any]] = [stations_by_id[station_id] for station_id in station_order]
  return {"stops": unique_stops}


def shapes_to_json(shapes: str) -> dict[str, list[dict[str, Any]]]:
  """Convert shapes.txt content into unique Leaflet-ready ordered coordinate lists."""
  reader: csv.DictReader[str] = csv.DictReader(io.StringIO(shapes))
  points_by_shape: dict[str, list[tuple[int, float, float]]] = {}
  shape_order: list[str] = []

  for row in reader:
    shape_id: str = (row.get("shape_id") or "").strip()
    sequence_raw: str = (row.get("shape_pt_sequence") or "").strip()
    lat_raw: str = (row.get("shape_pt_lat") or "").strip()
    lon_raw: str = (row.get("shape_pt_lon") or "").strip()

    if not shape_id or not sequence_raw or not lat_raw or not lon_raw:
      continue

    try:
      sequence: int = int(sequence_raw)
      lat: float = float(lat_raw)
      lon: float = float(lon_raw)
    except ValueError:
      continue

    if shape_id not in points_by_shape:
      points_by_shape[shape_id] = []
      shape_order.append(shape_id)

    points_by_shape[shape_id].append((sequence, lat, lon))

  unique_shapes_by_coordinates: dict[tuple[tuple[float, float], ...], dict[str, Any]] = {}
  for shape_id in shape_order:
    sorted_points: list[tuple[int, float, float]] = sorted(points_by_shape[shape_id], key=lambda point: point[0])
    coordinates: list[list[float]] = [[lat, lon] for _, lat, lon in sorted_points]
    coordinates_key: tuple[tuple[float, float], ...] = tuple((lat, lon) for lat, lon in coordinates)

    if coordinates_key not in unique_shapes_by_coordinates:
      unique_shapes_by_coordinates[coordinates_key] = {
        "shape_id": shape_id,
        "coordinates": coordinates,
        "other_ids": [],
      }
      continue

    duplicate_ids: list[str] = unique_shapes_by_coordinates[coordinates_key]["other_ids"]
    if shape_id != unique_shapes_by_coordinates[coordinates_key]["shape_id"] and shape_id not in duplicate_ids:
      duplicate_ids.append(shape_id)

  shapes_json: list[dict[str, Any]] = list(unique_shapes_by_coordinates.values())

  return {"shapes": shapes_json}


def main() -> None:
  """Read GTFS scheduled files, convert to JSON, and print them."""
  routes_by_id: dict[str, dict[str, str]] = load_routes_by_id()
  trips_by_id: dict[str, dict[str, str]] = load_trips_by_id()
  stop_times_by_trip: dict[str, dict[str, dict[str, str]]] = load_stop_times_by_trip()

  print(json.dumps(routes_by_id, ensure_ascii=False))
  print(json.dumps(trips_by_id, ensure_ascii=False))
  print(json.dumps(stop_times_by_trip, ensure_ascii=False))
  #with open("delete_stop_times_by_trip.json", "w", encoding="utf-8") as output_file:
    #json.dump(routes_by_id, output_file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
  main()
