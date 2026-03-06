"""Collect GTFS-Realtime vehicle positions for a short demo window."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import requests
from google.protobuf.json_format import MessageToDict
from google.transit import gtfs_realtime_pb2

METADATA_URL: str = (
  "https://fgc.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
  "vehicle-positions-gtfs_realtime/records?limit=1"
)
COLLECTION_SECONDS: int = 20
POLL_SECONDS: int = 5


def utc_now_iso() -> str:
  """Return current UTC time in ISO-8601 format."""
  return datetime.now(timezone.utc).isoformat()


def fetch_current_file(session: requests.Session) -> dict[str, Any]:
  """Fetch the current GTFS-RT file metadata from OpenDataSoft."""
  response: requests.Response = session.get(METADATA_URL, timeout=15)
  response.raise_for_status()
  payload: dict[str, Any] = response.json()
  return payload["results"][0]["file"]


def parse_feed(file_bytes: bytes) -> gtfs_realtime_pb2.FeedMessage:
  """Parse GTFS-Realtime protobuf bytes into a FeedMessage."""
  feed: gtfs_realtime_pb2.FeedMessage = gtfs_realtime_pb2.FeedMessage()
  feed.ParseFromString(file_bytes)
  return feed


def summarize_vehicle_entity(entity: gtfs_realtime_pb2.FeedEntity) -> dict[str, Any]:
  """Build a small printable summary for one vehicle entity."""
  vehicle = entity.vehicle
  trip = vehicle.trip
  position = vehicle.position
  descriptor = vehicle.vehicle
  return {
    "entity_id": entity.id,
    "vehicle_id": descriptor.id,
    "vehicle_label": descriptor.label,
    "route_id": trip.route_id,
    "trip_id": trip.trip_id,
    "latitude": position.latitude,
    "longitude": position.longitude,
    "bearing": position.bearing,
    "speed": position.speed,
    "event_timestamp": int(vehicle.timestamp) if vehicle.timestamp else None,
  }


def collect_for_window(duration_seconds: int, poll_seconds: int) -> None:
  """Collect and print GTFS-Realtime updates during the given window."""
  started_at: float = time.time()
  seen_file_ids: set[str] = set()
  snapshots: list[dict[str, Any]] = []

  with requests.Session() as session:
    while time.time() - started_at < duration_seconds:
      try:
        file_info: dict[str, Any] = fetch_current_file(session)
        file_id: str = file_info["id"]
        file_url: str = file_info["url"]

        if file_id in seen_file_ids:
          print(f"[{utc_now_iso()}] Same file_id {file_id}, skipping download")
          time.sleep(poll_seconds)
          continue

        file_response: requests.Response = session.get(file_url, timeout=30)
        file_response.raise_for_status() # f it's a 4xx (client error) or 5xx (server error), it raises an HTTPError with details of the failed request
        feed: gtfs_realtime_pb2.FeedMessage = parse_feed(file_response.content)

        vehicle_summaries: list[dict[str, Any]] = []
        first_vehicle_raw: dict[str, Any] | None = None

        for entity in feed.entity:
          print(entity)
          print("\n---\n")
          if not entity.HasField("vehicle"):
            continue
          vehicle_summaries.append(summarize_vehicle_entity(entity))
          if first_vehicle_raw is None:
            first_vehicle_raw = MessageToDict(
              entity.vehicle,
              preserving_proto_field_name=True,
            )

        snapshot: dict[str, Any] = {
          "collected_at": utc_now_iso(),
          "file_id": file_id,
          "file_name": file_info.get("filename"),
          "header_timestamp": int(feed.header.timestamp) if feed.header.timestamp else None,
          "vehicle_count": len(vehicle_summaries),
          "sample_vehicles": vehicle_summaries[:5],
          "first_vehicle_raw": first_vehicle_raw,
        }
        snapshots.append(snapshot)
        seen_file_ids.add(file_id)

        print("\n=== New GTFS-RT Snapshot ===")
        print(json.dumps(snapshot, indent=2, ensure_ascii=True))

      except requests.RequestException as error:
        print(f"[{utc_now_iso()}] HTTP error: {error}")
      except (KeyError, ValueError) as error:
        print(f"[{utc_now_iso()}] Parse error: {error}")

      time.sleep(poll_seconds)

  print("\n=== Collection Finished ===")
  print(f"Total unique snapshots collected: {len(snapshots)}")


def main() -> None:
  """Run a 20-second GTFS-Realtime collection demo."""
  print(
    "Collecting GTFS-Realtime vehicle positions "
    f"for {COLLECTION_SECONDS} seconds..."
  )
  collect_for_window(COLLECTION_SECONDS, POLL_SECONDS)


if __name__ == "__main__":
  main()
