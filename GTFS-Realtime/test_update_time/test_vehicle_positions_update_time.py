"""Measure average update time for GTFS-RT vehicle positions."""

from __future__ import annotations

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
SOURCE_NAME: str = "vehicle_positions"
TEST_DURATION_SECONDS: int = 20 * 60
POLL_SECONDS: int = 5

def parse_feed(file_bytes: bytes) -> gtfs_realtime_pb2.FeedMessage:
  """Parse GTFS-Realtime protobuf bytes into a FeedMessage."""
  feed: gtfs_realtime_pb2.FeedMessage = gtfs_realtime_pb2.FeedMessage()
  feed.ParseFromString(file_bytes)
  return feed

def utc_now_iso() -> str:
  """Return the current UTC timestamp in ISO-8601 format."""
  return datetime.now(timezone.utc).isoformat()


def fetch_current_file_id(session: requests.Session) -> str:
  """Fetch the current OpenDataSoft file id for the configured source."""
  response: requests.Response = session.get(METADATA_URL, timeout=15)
  response.raise_for_status()
  payload: dict[str, Any] = response.json()
  results: list[dict[str, Any]] = payload["results"]
  file_data: dict[str, Any] = results[0]["file"]
  file_id: str = str(file_data["id"])
  return file_id, str(file_data["url"])


def run_update_time_test(duration_seconds: int, poll_seconds: int) -> None:
  """Poll source metadata and print average time between new file ids."""
  started_at: float = time.monotonic()
  seen_file_ids: set[str] = set()
  update_intervals_seconds: list[float] = []
  last_update_at: float | None = None

  print(
    f"[{utc_now_iso()}] Starting update-time test for {SOURCE_NAME} "
    f"for {duration_seconds} seconds"
  )

  with requests.Session() as session:
    while time.monotonic() - started_at < duration_seconds:
      try:
        file_id: str = fetch_current_file_id(session)
        print(file_id)                                # 'https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/vehicle-positions-gtfs_realtime/files/d286964db2d107ecdb1344bf02f7b27b'
        file_response: requests.Response = session.get("https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/vehicle-positions-gtfs_realtime/files/d286964db2d107ecdb1344bf02f7b27b", timeout=30)
        file_response.raise_for_status()
        feed: gtfs_realtime_pb2.FeedMessage = parse_feed(file_response.content)
        print(feed.header)

        break

        """
        header {
  gtfs_realtime_version: "2.0"
  incrementality: FULL_DATASET
  timestamp: 1771527125
}
        
        """

        if file_id in seen_file_ids:
          print(f"[{utc_now_iso()}] Same file_id {file_id}, no update")
          time.sleep(poll_seconds)
          continue

        now_monotonic: float = time.monotonic()
        seen_file_ids.add(file_id)

        if last_update_at is None:
          print(f"[{utc_now_iso()}] First update detected with file_id={file_id}")
        else:
          interval_seconds: float = now_monotonic - last_update_at
          update_intervals_seconds.append(interval_seconds)
          print(
            f"[{utc_now_iso()}] New file_id={file_id}. "
            f"Interval since previous update: {interval_seconds:.2f}s"
          )

        last_update_at = now_monotonic

      except requests.RequestException as error:
        print(f"[{utc_now_iso()}] HTTP error: {error}")
      except (KeyError, IndexError, TypeError, ValueError) as error:
        print(f"[{utc_now_iso()}] Parse error: {error}")

      time.sleep(poll_seconds)

  print(f"\n[{utc_now_iso()}] Test finished for {SOURCE_NAME}")
  print(f"Unique file ids seen: {len(seen_file_ids)}")

  if update_intervals_seconds:
    average_seconds: float = sum(update_intervals_seconds) / len(update_intervals_seconds)
    print(f"Average update time: {average_seconds:.2f}s")
    print(f"Update intervals counted: {len(update_intervals_seconds)}")
  else:
    print("Average update time: not available (fewer than 2 updates detected)")


def main() -> None:
  """Execute the 20-minute polling test for vehicle positions."""
  run_update_time_test(TEST_DURATION_SECONDS, POLL_SECONDS)


if __name__ == "__main__":
  main()
