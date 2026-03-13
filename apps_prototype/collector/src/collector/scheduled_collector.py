import requests
import json
import csv
import io
from typing import Any

URL: str = "https://fgc.opendatasoft.com/api/explore/v2.1/catalog/datasets/gtfs_zip/records"
SAVE_PATH: str = "../GTFS-Scheduled-data"

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


def scheduled_collection() -> None:
  """Fetch scheduled GTFS files and print station-level stops JSON."""
  try:
    response: requests.Response = requests.get(url=URL)
    response.raise_for_status()
    records: dict[str, Any] = json.loads(response.text)

    for item in records["results"]:
      file_response: requests.Response = requests.get(item["file"]["url"])
      file_response.raise_for_status()
      if item["file"]["filename"] == "stops.txt":
        stops_json: dict[str, list[dict[str, Any]]] = stops_to_json(file_response.text)
        with open("../../../outputs/stops.json", "w", encoding="utf-8") as output_file:
          json.dump(stops_json, output_file, ensure_ascii=False, indent=2)
      if item["file"]["filename"] == "shapes.txt":
        shapes_json: dict[str, list[dict[str, Any]]] = shapes_to_json(file_response.text)
        with open("../../../outputs/shapes.json", "w", encoding="utf-8") as output_file:
          json.dump(shapes_json, output_file, ensure_ascii=False, ident=2)
      path: str = SAVE_PATH + "/" + item["file"]["filename"]
      with open(path, "w", encoding="utf-8") as output_file:
        output_file.write(file_response.text)
  except requests.exceptions.HTTPError as error:
    print(type(error).__name__)
    raise
  except requests.exceptions.ConnectionError as error:
    print(type(error).__name__)
    raise
  except requests.exceptions.ReadTimeout as error:
    print(type(error).__name__)
    raise
  except requests.exceptions.RequestException as error:
    print(type(error).__name__)
    raise


def main() -> None:
  """Run scheduled data collection."""
  scheduled_collection()

if __name__ == "__main__":
  main()
