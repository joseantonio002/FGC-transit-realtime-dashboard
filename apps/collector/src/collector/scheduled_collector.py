import requests
import json
from typing import Any
from load_gtfs_scheduled import stops_to_json, shapes_to_json

URL: str = "https://fgc.opendatasoft.com/api/explore/v2.1/catalog/datasets/gtfs_zip/records"
SAVE_PATH_TXT: str = "./GTFS-Scheduled-data"
SAVE_PATH_VOLUME: str = "./outputs"

def scheduled_collector() -> None:
  """Fetch scheduled GTFS files, save them to .txt and stops and shapes to json"""
  try:
    response: requests.Response = requests.get(url=URL)
    response.raise_for_status()
    records: dict[str, Any] = json.loads(response.text)

    for item in records["results"]:
      file_response: requests.Response = requests.get(item["file"]["url"])
      file_response.raise_for_status()
      if item["file"]["filename"] == "stops.txt":
        stops_json: dict[str, list[dict[str, Any]]] = stops_to_json(file_response.text)
        path: str = SAVE_PATH_VOLUME + "/stops.json"
        with open(path, "w", encoding="utf-8") as output_file:
          json.dump(stops_json, output_file, ensure_ascii=False, indent=2)
      if item["file"]["filename"] == "shapes.txt":
        shapes_json: dict[str, list[dict[str, Any]]] = shapes_to_json(file_response.text)
        path: str = SAVE_PATH_VOLUME + "/shapes.json"
        with open(path, "w", encoding="utf-8") as output_file:
          json.dump(shapes_json, output_file, ensure_ascii=False, indent=2)
      path: str = SAVE_PATH_TXT + "/" + item["file"]["filename"]
      with open(path, "w", encoding="utf-8") as output_file:
        output_file.write(file_response.text)
  except Exception as error:
    raise


def main() -> None:
  """Run scheduled data collection."""
  scheduled_collector()

if __name__ == "__main__":
  main()
