from __future__ import annotations
from typing import Any
from gtfs_to_json import _calculate_delay_seconds, _convert_hhmmss_to_epoch, SERVICE_START_DATE_FIELD
from sqlitle_functions import insert_historic_delay_row
from datetime import datetime

def _format_delay(delay_seconds: int) -> str:
  """Format delay seconds into signed minutes and seconds string."""
  sign: str = "-" if delay_seconds < 0 else ""
  abs_delay: int = abs(delay_seconds)
  minutes: int = abs_delay // 60
  seconds: int = abs_delay % 60
  return f"{sign}{minutes}m {seconds}s"

def _store_stop_delay(
  trip_id: str,
  stop_id: str,
  arrival_time_epoch: int | None,
  sh_stop_times: dict[str, dict[str, dict[str, str]]],
  sh_trips,
  feed_start_service_date,
  cursor,
  connection
) -> None:
  """Store stop delay details for one reached stop."""
  scheduled_trip: dict[str, dict[str, str]] | None = sh_stop_times.get(trip_id)
  if scheduled_trip is None or stop_id not in scheduled_trip:
    print(f"The trip {trip_id} is not in scheduled")
    return

  scheduled_stop: dict[str, str] = scheduled_trip[stop_id]
  stop_sequence: str = scheduled_stop.get("stop_sequence", "") or "unknown"
  scheduled_arrival_time: str = scheduled_stop.get("arrival_time", "") or "unknown"

  delay_seconds: int | None = _calculate_delay_seconds(arrival_time_epoch, scheduled_arrival_time, feed_start_service_date)
  if delay_seconds is None:
    #delay_formatted: str = "unknown"
    print(f"Error calculating delay for trip {trip_id}, could not calculate delay, some fields missing")
    return
  else:
    delay_formatted = _format_delay(delay_seconds)

  route_id = sh_trips[trip_id].get("route_id", "") or "unknown"
  arrival_planned = _convert_hhmmss_to_epoch(scheduled_arrival_time, feed_start_service_date, arrival_time_epoch)

  execution_datetime = datetime.now()

  row = {
    "trip_id": trip_id,
    "route_id": route_id,
    "stop_id": stop_id,
    "stop_sequence": stop_sequence,
    "arrival_delay_total_seconds": delay_seconds,
    "arrival_delay_formatted": delay_formatted,
    "arrival_planned": arrival_planned,
    "arrival_real": arrival_time_epoch,
    "execution_datetime": str(execution_datetime)
  }

  insert_historic_delay_row(cursor, connection, row)


def _is_only_last_stop_remaining(
  trip_id: str,
  previous_trip: dict[str, dict[str, Any]],
  sh_stop_times: dict[str, dict[str, dict[str, str]]],
) -> bool:
  """Return true when previous snapshot contains only the trip final stop."""
  if len(previous_trip) != 1:
    return False

  scheduled_trip: dict[str, dict[str, str]] | None = sh_stop_times.get(trip_id)
  if scheduled_trip is None or len(scheduled_trip) == 0:
    return False

  max_sequence: int | None = None
  last_stop_id: str | None = None
  for scheduled_stop_id, scheduled_stop in scheduled_trip.items():
    stop_sequence_raw: str = scheduled_stop.get("stop_sequence", "")
    try:
      sequence: int = int(stop_sequence_raw)
    except ValueError:
      continue

    if max_sequence is None or sequence > max_sequence:
      max_sequence = sequence
      last_stop_id = scheduled_stop_id

  if last_stop_id is None:
    return False

  remaining_stop_id: str = next(iter(previous_trip.keys()))
  return remaining_stop_id == last_stop_id


def calculate_delays(
  current_feed: dict[str, dict[str, dict[str, Any]]],
  previous_feed: dict[str, dict[str, dict[str, Any]]],
  sh_stop_times: dict[str, dict[str, dict[str, str]]],
  sh_trips: dict[str, dict[str, Any]],
  cursor, 
  connection
) -> None:
  """Print delays when stops disappear from trip updates between snapshots."""
  feed_start_service_date = current_feed[SERVICE_START_DATE_FIELD] 
  for trip_id, current_trip in current_feed.items():
    if trip_id == SERVICE_START_DATE_FIELD:
      continue
    previous_trip: dict[str, dict[str, Any]] | None = previous_feed.get(trip_id)
    if previous_trip is None:
      continue

    for stop_id, previous_stop_info in previous_trip.items():
      if stop_id in current_trip:
        continue
      arrival_time_epoch_raw: Any = previous_stop_info.get("arrival_time")
      arrival_time_epoch: int | None = int(arrival_time_epoch_raw) if arrival_time_epoch_raw is not None else None
      _store_stop_delay(trip_id, stop_id, arrival_time_epoch, sh_stop_times, sh_trips, feed_start_service_date, cursor, connection)

  for trip_id, previous_trip in previous_feed.items():
    if trip_id in current_feed:
      continue

    if not _is_only_last_stop_remaining(trip_id, previous_trip, sh_stop_times):
      continue

    print(f"{trip_id} finished, delay for remaning stops")
    for stop_id, previous_stop_info in previous_trip.items():
      arrival_time_epoch_raw: Any = previous_stop_info.get("arrival_time")
      arrival_time_epoch: int | None = int(arrival_time_epoch_raw) if arrival_time_epoch_raw is not None else None
      _store_stop_delay(trip_id, stop_id, arrival_time_epoch, sh_stop_times, sh_trips, feed_start_service_date, cursor, connection)
