"""Measure average update time for GTFS-RT vehicle positions."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import requests
from google.protobuf.message import DecodeError
from google.transit import gtfs_realtime_pb2

FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/vehicle-positions-gtfs_realtime/files/d286964db2d107ecdb1344bf02f7b27b"
SOURCE_NAME: str = "vehicle_positions"
TEST_DURATION_SECONDS: int = 20 * 60
POLL_SECONDS: int = 5


def utc_now_iso() -> str:
  """Return the current UTC timestamp in ISO-8601 format."""
  return datetime.now(timezone.utc).isoformat()


def fetch_feed_header_timestamp(session: requests.Session) -> int:
  """Download GTFS-RT protobuf and return header timestamp."""
  response: requests.Response = session.get(FEED_URL, timeout=30)
  response.raise_for_status()
  feed: gtfs_realtime_pb2.FeedMessage = gtfs_realtime_pb2.FeedMessage()
  feed.ParseFromString(response.content)
  return int(feed.header.timestamp)


def run_update_time_test(duration_seconds: int, poll_seconds: int) -> None:
  """Poll source feed and print average time between new header timestamps."""
  started_at: float = time.monotonic()
  seen_header_timestamps: set[int] = set()
  update_intervals_seconds: list[float] = []
  last_update_at: float | None = None

  print(
    f"[{utc_now_iso()}] Starting update-time test for {SOURCE_NAME} "
    f"for {duration_seconds} seconds"
  )

  with requests.Session() as session:
    while time.monotonic() - started_at < duration_seconds:
      try:
        header_timestamp: int = fetch_feed_header_timestamp(session)

        if header_timestamp in seen_header_timestamps:
          print(
            f"[{utc_now_iso()}] Same header.timestamp {header_timestamp}, no update"
          )
          time.sleep(poll_seconds)
          continue

        now_monotonic: float = time.monotonic()
        seen_header_timestamps.add(header_timestamp)

        if last_update_at is None:
          print(
            f"[{utc_now_iso()}] First update detected with "
            f"header.timestamp={header_timestamp}"
          )
        else:
          interval_seconds: float = now_monotonic - last_update_at
          update_intervals_seconds.append(interval_seconds)
          print(
            f"[{utc_now_iso()}] New header.timestamp={header_timestamp}. "
            f"Interval since previous update: {interval_seconds:.2f}s"
          )

        last_update_at = now_monotonic

      except requests.RequestException as error:
        print(f"[{utc_now_iso()}] HTTP error: {error}")
      except (DecodeError, ValueError) as error:
        print(f"[{utc_now_iso()}] Parse error: {error}")

      time.sleep(poll_seconds)

  print(f"\n[{utc_now_iso()}] Test finished for {SOURCE_NAME}")
  print(f"Unique header timestamps seen: {len(seen_header_timestamps)}")

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
