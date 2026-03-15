"""Transform GTFS-Realtime feeds to JSON payloads."""

from __future__ import annotations

from typing import Any

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


def vehicles_to_json(vehicles_feed: Any, sh_trips: dict[str, dict[str, Any]], sh_routes, sh_stops) -> dict[str, list[dict[str, Any]]]:
  """Convert the vehicle positions feed into the API output format."""
  output: dict[str, list[dict[str, Any]]] = {"vehicles": []}

  for vehicle_to_process in vehicles_feed.entity:
    trip_id: str = vehicle_to_process.vehicle.trip.trip_id
    route_short_name: str | None = None
    route_color: str = None

    if trip_id in sh_trips:
      route_short_name = sh_trips[trip_id].get("route_id")
      route_color = sh_routes[route_short_name].get("route_color")

    next_stop: str = _get_stop_name(vehicle_to_process.vehicle.stop_id, sh_stops)

    vehicle_output: dict[str, Any] = {
      "route_short_name": route_short_name,
      "next_stop": next_stop,
      "occupancy_status": _occupancy_status_name(vehicle_to_process.vehicle),
      "latitude": vehicle_to_process.vehicle.position.latitude,
      "longitude": vehicle_to_process.vehicle.position.longitude,
      "route_color": route_color,
    }

    output["vehicles"].append(vehicle_output)

  return output
