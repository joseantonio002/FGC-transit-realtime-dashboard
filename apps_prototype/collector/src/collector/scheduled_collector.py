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
        with open("./stops.json", "w", encoding="utf-8") as output_file:
          json.dump(stops_json, output_file, ensure_ascii=False, indent=2)
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
