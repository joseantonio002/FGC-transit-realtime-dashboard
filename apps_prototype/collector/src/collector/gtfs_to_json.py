"""Transform GTFS-Realtime feeds to JSON payloads."""

from __future__ import annotations

from typing import Any
from datetime import datetime
from zoneinfo import ZoneInfo


AGENCY_TIMEZONE: ZoneInfo = ZoneInfo("Europe/Madrid")
DELAY_SECONDS: int = 300

def _occupancy_status_name(vehicle: Any) -> str:
  """Resolve a readable occupancy status name from a vehicle message."""
  status_value: int = int(vehicle.occupancy_status)

  try:
    return str(vehicle.OccupancyStatus.Name(status_value))
  except Exception:
    return str(status_value)

def _get_stop_name(stop_id: str, sh_stops: dict[str, Any]) -> str:
  """Get the stop name for a given stop ID."""
  for stop in sh_stops['stops']:
    if stop['stop_id'] == stop_id:
      return stop['stop_name']
  return "Unknown Stop"


def _parse_hhmmss_to_seconds(value: str) -> int | None:
  """Convert a HH:MM:SS GTFS scheduled time into absolute seconds."""
  time_parts: list[str] = value.split(":")
  if len(time_parts) != 3:
    return None

  try:
    hours: int = int(time_parts[0])
    minutes: int = int(time_parts[1])
    seconds: int = int(time_parts[2])
  except ValueError:
    return None

  if minutes < 0 or minutes > 59 or seconds < 0 or seconds > 59 or hours < 0:
    return None

  return (hours * 3600) + (minutes * 60) + seconds


def _service_midnight_epoch(start_date_raw: str, fallback_epoch: int) -> int:
  """Build the service-day midnight epoch in the agency timezone."""
  try:
    if len(start_date_raw) != 8:
      raise ValueError("Invalid start_date")

    year: int = int(start_date_raw[0:4])
    month: int = int(start_date_raw[4:6])
    day: int = int(start_date_raw[6:8])
    service_midnight: datetime = datetime(year, month, day, 0, 0, 0, tzinfo=AGENCY_TIMEZONE)
    return int(service_midnight.timestamp())
  except Exception:
    fallback_dt: datetime = datetime.fromtimestamp(fallback_epoch, tz=AGENCY_TIMEZONE)
    fallback_midnight: datetime = datetime(
      fallback_dt.year,
      fallback_dt.month,
      fallback_dt.day,
      0,
      0,
      0,
      tzinfo=AGENCY_TIMEZONE,
    )
    return int(fallback_midnight.timestamp())


def _get_schedule_state(
  trip_id: str,
  trips: Any,
  sh_stop_times: dict[str, dict[str, dict[str, str]]],
) -> str:
  """Return schedule state by comparing realtime and planned arrival epochs."""
  if trip_id not in sh_stop_times:
    return "unknown"

  for entity in trips.entity:
    if not entity.HasField("trip_update"):
      continue

    trip_update: Any = entity.trip_update
    if trip_update.trip.trip_id != trip_id:
      continue

    if not trip_update.stop_time_update:
      return "unknown"

    current_stop_update: Any = trip_update.stop_time_update[0]
    stop_id: str = str(current_stop_update.stop_id)

    if stop_id not in sh_stop_times[trip_id]:
      return "unknown"

    scheduled_arrival_raw: str = sh_stop_times[trip_id][stop_id].get("arrival_time", "")
    scheduled_arrival_seconds: int | None = _parse_hhmmss_to_seconds(scheduled_arrival_raw)
    if scheduled_arrival_seconds is None:
      return "unknown"

    if not current_stop_update.arrival.HasField("time"):
      return "unknown"

    realtime_arrival_epoch: int = int(current_stop_update.arrival.time)
    start_date_raw: str = str(trip_update.trip.start_date or "")
    service_midnight_epoch: int = _service_midnight_epoch(start_date_raw, realtime_arrival_epoch)
    planned_arrival_epoch: int = service_midnight_epoch + scheduled_arrival_seconds
    delay_seconds: int = realtime_arrival_epoch - planned_arrival_epoch

    if delay_seconds >= DELAY_SECONDS:
      return "late"
    return "on time"

  return "unknown"


def vehicles_to_json(vehicles_feed: Any, sh_trips: dict[str, dict[str, Any]], sh_routes, sh_stops, sh_stop_times, trips) -> dict[str, list[dict[str, Any]]]:
  """Convert the vehicle positions feed into the API output format."""
  output: dict[str, list[dict[str, Any]]] = {"vehicles": []}

  for vehicle_to_process in vehicles_feed.entity:
    trip_id: str = vehicle_to_process.vehicle.trip.trip_id
    route_short_name: str | None = None
    route_color: str | None = None

    if trip_id in sh_trips:
      route_short_name = sh_trips[trip_id].get("route_id")
      if route_short_name in sh_routes:
        route_color = sh_routes[route_short_name].get("route_color")

    next_stop: str = _get_stop_name(vehicle_to_process.vehicle.stop_id, sh_stops)
    schedule_state: str = _get_schedule_state(trip_id, trips, sh_stop_times)

    vehicle_output: dict[str, Any] = {
      "route_short_name": route_short_name,
      "next_stop": next_stop,
      "occupancy_status": _occupancy_status_name(vehicle_to_process.vehicle),
      "latitude": vehicle_to_process.vehicle.position.latitude,
      "longitude": vehicle_to_process.vehicle.position.longitude,
      "route_color": route_color,
      "schedule_state": schedule_state,
    }

    output["vehicles"].append(vehicle_output)

  return output
