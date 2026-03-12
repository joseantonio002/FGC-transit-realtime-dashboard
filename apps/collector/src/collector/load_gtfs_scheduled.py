import csv
import json
from pathlib import Path


BASE_GTFS_SCHEDULED_PATH: Path = (Path(__file__).resolve().parent / "../GTFS-Scheduled-data").resolve()
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


def main() -> None:
  """Read GTFS scheduled files, convert to JSON, and print them."""
  routes_by_id: dict[str, dict[str, str]] = load_routes_by_id()
  trips_by_id: dict[str, dict[str, str]] = load_trips_by_id()
  stop_times_by_trip: dict[str, dict[str, dict[str, str]]] = load_stop_times_by_trip()

  #print(json.dumps(routes_by_id, ensure_ascii=False))
  #print(json.dumps(trips_by_id, ensure_ascii=False))
  #print(json.dumps(stop_times_by_trip, ensure_ascii=False))
  with open("delete_stop_times_by_trip.json", "w", encoding="utf-8") as output_file:
    json.dump(stop_times_by_trip, output_file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
  main()
