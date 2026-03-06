"""Measure lingering time of stop updates after STOPPED_AT events."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from google.protobuf.message import DecodeError
from google.transit import gtfs_realtime_pb2

TRIP_UPDATES_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/trip-updates-gtfs_realtime/files/735985017f62fd33b2fe46e31ce53829"
VEHICLE_POSITIONS_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/vehicle-positions-gtfs_realtime/files/d286964db2d107ecdb1344bf02f7b27b"
TEST_DURATION_SECONDS: int = 60 * 20
POLL_SECONDS: int = 10


@dataclass
class ActiveSample:
  """Represent a stop lingering sample currently being tracked."""

  trip_id: str
  stop_id: str
  started_at_epoch_seconds: float


@dataclass
class CompletedSample:
  """Represent a completed lingering sample."""

  trip_id: str
  stop_id: str
  lingering_seconds: float


@dataclass
class StoppedEvent:
  """Represent a STOPPED_AT event from vehicle_positions."""

  stop_id: str
  stop_sequence: int


@dataclass
class TripUpdateIndex:
  """Represent quick lookup structures for trip_updates stop entries."""

  stop_ids: set[str]
  stop_id_by_sequence: dict[int, str]


def utc_now_iso() -> str:
  """Return the current UTC timestamp in ISO-8601 format."""
  return datetime.now(timezone.utc).isoformat()


def fetch_feed(session: requests.Session, feed_url: str) -> gtfs_realtime_pb2.FeedMessage:
  """Download GTFS-RT protobuf and return parsed feed."""
  response: requests.Response = session.get(feed_url, timeout=30)
  response.raise_for_status()
  feed: gtfs_realtime_pb2.FeedMessage = gtfs_realtime_pb2.FeedMessage()
  feed.ParseFromString(response.content)
  return feed


def extract_stopped_trip_stops(feed: gtfs_realtime_pb2.FeedMessage) -> dict[str, StoppedEvent]:
  """Return trip_id -> STOPPED_AT event for first entity per trip."""
  stopped_by_trip: dict[str, StoppedEvent] = {}

  for entity in feed.entity:
    if not entity.HasField("vehicle"):
      continue

    vehicle: gtfs_realtime_pb2.VehiclePosition = entity.vehicle
    trip_id: str = vehicle.trip.trip_id.strip()
    stop_id: str = vehicle.stop_id.strip()

    if not trip_id or not stop_id:
      continue

    if vehicle.current_status != gtfs_realtime_pb2.VehiclePosition.STOPPED_AT:
      continue

    if trip_id in stopped_by_trip:
      print(
        f"[{utc_now_iso()}] Duplicate vehicle_positions entities for trip_id="
        f"{trip_id}; using first entity"
      )
      continue

    stopped_by_trip[trip_id] = StoppedEvent(
      stop_id=stop_id,
      stop_sequence=int(vehicle.current_stop_sequence),
    )

  return stopped_by_trip


def extract_trip_update_stops(feed: gtfs_realtime_pb2.FeedMessage) -> dict[str, TripUpdateIndex]:
  """Return trip_id -> stop index from first trip_updates entity per trip."""
  stops_by_trip: dict[str, TripUpdateIndex] = {}

  for entity in feed.entity:
    if not entity.HasField("trip_update"):
      continue

    trip_update: gtfs_realtime_pb2.TripUpdate = entity.trip_update
    trip_id: str = trip_update.trip.trip_id.strip()
    if not trip_id:
      continue

    if trip_id in stops_by_trip:
      print(
        f"[{utc_now_iso()}] Duplicate trip_updates entities for trip_id="
        f"{trip_id}; using first entity"
      )
      continue

    stop_ids: set[str] = set()
    stop_id_by_sequence: dict[int, str] = {}
    for stop_time_update in trip_update.stop_time_update:
      stop_id: str = stop_time_update.stop_id.strip()
      if stop_id:
        stop_ids.add(stop_id)
      stop_sequence: int = int(stop_time_update.stop_sequence)
      if stop_sequence > 0 and stop_id and stop_sequence not in stop_id_by_sequence:
        stop_id_by_sequence[stop_sequence] = stop_id

    stops_by_trip[trip_id] = TripUpdateIndex(
      stop_ids=stop_ids,
      stop_id_by_sequence=stop_id_by_sequence,
    )

  return stops_by_trip


def calculate_mean(values: list[float]) -> float:
  """Return mean value or 0.0 when list is empty."""
  if not values:
    return 0.0
  return float(statistics.mean(values))


def calculate_stddev(values: list[float]) -> float:
  """Return sample standard deviation or 0.0 when undefined."""
  if len(values) < 2:
    return 0.0
  return float(statistics.stdev(values))


def run_lingering_time_test(
  duration_seconds: int,
  poll_seconds: int,
) -> tuple[list[CompletedSample], list[ActiveSample]]:
  """Track stop lingering time samples for the configured window."""
  started_at_monotonic: float = time.monotonic()
  active_samples: dict[tuple[str, str], ActiveSample] = {}
  completed_samples: list[CompletedSample] = []
  censored_samples: list[ActiveSample] = []
  last_started_stop_by_trip: dict[str, str] = {}

  print(
    f"[{utc_now_iso()}] Starting lingering-time test for {duration_seconds} "
    f"seconds (poll every {poll_seconds}s)"
  )

  with requests.Session() as session:
    while time.monotonic() - started_at_monotonic < duration_seconds:
      now_epoch_seconds: float = time.time()

      try:
        vehicle_positions_feed: gtfs_realtime_pb2.FeedMessage = fetch_feed(
          session,
          VEHICLE_POSITIONS_FEED_URL,
        )
        trip_updates_feed: gtfs_realtime_pb2.FeedMessage = fetch_feed(
          session,
          TRIP_UPDATES_FEED_URL,
        )
      except requests.RequestException as error:
        print(f"[{utc_now_iso()}] HTTP error: {error}")
        time.sleep(poll_seconds)
        continue
      except (DecodeError, ValueError) as error:
        print(f"[{utc_now_iso()}] Parse error: {error}")
        time.sleep(poll_seconds)
        continue

      stopped_by_trip: dict[str, StoppedEvent] = extract_stopped_trip_stops(
        vehicle_positions_feed
      )
      trip_update_stops_by_trip: dict[str, TripUpdateIndex] = extract_trip_update_stops(
        trip_updates_feed
      )

      for trip_id, stopped_event in stopped_by_trip.items():
        stop_id: str = stopped_event.stop_id
        stop_sequence: int = stopped_event.stop_sequence

        if trip_id not in trip_update_stops_by_trip:
          print(
            f"[{utc_now_iso()}] Skipping sample trip_id={trip_id}, stop_id="
            f"{stop_id}; trip missing in trip_updates"
          )
          continue

        trip_update_index: TripUpdateIndex = trip_update_stops_by_trip[trip_id]
        tracked_stop_id: str = stop_id

        if stop_id not in trip_update_index.stop_ids:
          remapped_stop_id: str | None = trip_update_index.stop_id_by_sequence.get(
            stop_sequence
          )
          if remapped_stop_id is None:
            print(
              f"[{utc_now_iso()}] Skipping sample trip_id={trip_id}, stop_id="
              f"{stop_id}; stop missing in trip_updates"
            )
            continue

          tracked_stop_id = remapped_stop_id
          print(
            f"[{utc_now_iso()}] Remapped stop by sequence for trip_id={trip_id}: "
            f"vehicle_positions stop_id={stop_id} -> trip_updates stop_id="
            f"{tracked_stop_id} (sequence={stop_sequence})"
          )

        sample_key: tuple[str, str] = (trip_id, tracked_stop_id)
        if sample_key in active_samples:
          continue

        if last_started_stop_by_trip.get(trip_id) == tracked_stop_id:
          continue

        active_samples[sample_key] = ActiveSample(
          trip_id=trip_id,
          stop_id=tracked_stop_id,
          started_at_epoch_seconds=now_epoch_seconds,
        )
        last_started_stop_by_trip[trip_id] = tracked_stop_id
        print(
          f"[{utc_now_iso()}] Started sample trip_id={trip_id}, "
          f"stop_id={tracked_stop_id}"
        )

      for sample_key in list(active_samples.keys()):
        sample: ActiveSample = active_samples[sample_key]
        trip_id: str = sample.trip_id
        stop_id: str = sample.stop_id

        if trip_id not in trip_update_stops_by_trip:
          censored_samples.append(sample)
          del active_samples[sample_key]
          print(
            f"[{utc_now_iso()}] Censored sample trip_id={trip_id}, "
            f"stop_id={stop_id}; trip disappeared from trip_updates"
          )
          continue

        if stop_id in trip_update_stops_by_trip[trip_id].stop_ids:
          continue

        lingering_seconds: float = now_epoch_seconds - sample.started_at_epoch_seconds
        completed_samples.append(
          CompletedSample(
            trip_id=trip_id,
            stop_id=stop_id,
            lingering_seconds=lingering_seconds,
          )
        )
        del active_samples[sample_key]
        print(
          f"[{utc_now_iso()}] Completed sample trip_id={trip_id}, "
          f"stop_id={stop_id}, lingering={lingering_seconds:.2f}s"
        )

      time.sleep(poll_seconds)

  for sample in active_samples.values():
    censored_samples.append(sample)
    print(
      f"[{utc_now_iso()}] Censored sample trip_id={sample.trip_id}, "
      f"stop_id={sample.stop_id}; test window ended"
    )

  return completed_samples, censored_samples


def print_report(
  completed_samples: list[CompletedSample],
  censored_samples: list[ActiveSample],
) -> None:
  """Print per-trip and global lingering-time statistics."""
  print(f"\n[{utc_now_iso()}] Lingering-time test finished")
  print(f"Samples collected: {len(completed_samples)}")
  print(f"Censored samples: {len(censored_samples)}")

  durations_by_trip: dict[str, list[float]] = {}
  for sample in completed_samples:
    durations_by_trip.setdefault(sample.trip_id, []).append(sample.lingering_seconds)

  if durations_by_trip:
    print("\nPer-trip stats (count, mean_s, stddev_s):")
    for trip_id in sorted(durations_by_trip.keys()):
      values: list[float] = durations_by_trip[trip_id]
      print(
        f"- trip_id={trip_id} count={len(values)} "
        f"mean={calculate_mean(values):.2f} stddev={calculate_stddev(values):.2f}"
      )
  else:
    print("\nPer-trip stats: no completed samples")

  all_values: list[float] = [sample.lingering_seconds for sample in completed_samples]
  print("\nGlobal stats:")
  print(f"- mean={calculate_mean(all_values):.2f}s")
  print(f"- stddev={calculate_stddev(all_values):.2f}s")


def test_stop_time_update_lingering_time() -> None:
  """Measure stop-update lingering distribution using vehicle stop events."""
  completed_samples, censored_samples = run_lingering_time_test(
    TEST_DURATION_SECONDS,
    POLL_SECONDS,
  )
  print_report(completed_samples, censored_samples)
  if not completed_samples:
    print(f"[{utc_now_iso()}] WARNING: no lingering samples collected")


def main() -> None:
  """Execute lingering-time test as a standalone script."""
  test_stop_time_update_lingering_time()


if __name__ == "__main__":
  main()
