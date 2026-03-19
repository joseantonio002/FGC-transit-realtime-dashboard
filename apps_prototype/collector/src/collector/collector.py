import time
import requests
from load_gtfs_scheduled import load_routes_by_id, load_stop_times_by_trip, load_trips_by_id
from scheduled_collector import scheduled_collector, SAVE_PATH_JSON
from get_current_snapshot import obtain_last_snapshots
from gtfs_to_json import vehicles_to_json, arrival_times_to_json, trips_feed_to_dict
from calculate_delays import calculate_delays
import json

import sqlitle_functions
import sqlite3


TRIP_UPDATES_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/trip-updates-gtfs_realtime/files/735985017f62fd33b2fe46e31ce53829"
VEHICLE_POSITIONS_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/vehicle-positions-gtfs_realtime/files/d286964db2d107ecdb1344bf02f7b27b"
POLL_SECONDS: int = 10
TIMEOUT: int = 3

NUMBER_RETRIES: int = 10
RETRY_DELAY_SECONDS: int = 5
SLEEP_TIME: int = 100

COUNT_LOAD_GTFS_SCHEDULED_AGAIN: int = 200


def new_session() -> requests.Session:
  """Create a new HTTP session."""
  s: requests.Session = requests.Session()
  return s


def backoff(backoff_counter: int) -> None:
  """Sleep using exponential backoff after repeated failures."""
  print(
    "Exponential backoff activated "
    f"{backoff_counter} times in a row, sleeping for 2^{backoff_counter} seconds"
  )
  time.sleep(2 ** backoff_counter)


def main() -> None:
  """Continuously fetch newest vehicles and trip snapshots."""
  s: requests.Session = new_session()
  trips_current_ts: int = -1
  vh_current_ts: int = -1
  backoff_counter: int = 0

  conn: sqlite3.Connection = sqlite3.connect("datos.db")
  sqlitle_db: sqlite3.Cursor = conn.cursor()
  sqlitle_functions.create_historic_table(sqlitle_db, conn)
  

  scheduled_collector()
  gtfs_scheduled_load_again: int = 0
  with open(SAVE_PATH_JSON + '/stops.json', 'r') as stops:
    sh_stops = json.load(stops)
  sh_trips = load_trips_by_id()
  sh_routes = load_routes_by_id()
  sh_stop_times = load_stop_times_by_trip()

  previous_trip_feed = {}

  while True:
    try:
      vh, vh_current_ts, trips, trips_current_ts, return_status = obtain_last_snapshots(
        s=s,
        vh_previous_ts=vh_current_ts,
        trips_previous_ts=trips_current_ts,
        vehicle_positions_feed_url=VEHICLE_POSITIONS_FEED_URL,
        trip_updates_feed_url=TRIP_UPDATES_FEED_URL,
        timeout=TIMEOUT,
        number_retries=NUMBER_RETRIES,
        retry_delay_seconds=RETRY_DELAY_SECONDS,
      )
    except requests.exceptions.HTTPError as e:
      status: int = e.response.status_code
      print(f"HTTP Error fetching data: {status}")
      backoff_counter += 1
      backoff(backoff_counter)
      continue
    except requests.exceptions.ConnectionError:
      print("Connection error, reseting connection")
      s.close()
      s = new_session()
      backoff_counter += 1
      backoff(backoff_counter)
      continue
    except requests.exceptions.ReadTimeout:
      print("Time out")
      backoff_counter += 1
      backoff(backoff_counter)
      continue
    except requests.exceptions.RequestException as request_error:
      print("Exception request")
      raise request_error
    except Exception as e:
      backoff_counter += 1
      backoff(backoff_counter)
      continue

    backoff_counter = 0
    gtfs_scheduled_load_again += 1

    if return_status == 0:
      print("Skipping execution because vehicles was not updated")
    elif return_status == 1:
      print("Vehicles was updated but trips not")
      print(vh.entity[0])
    else:
      print(f"Both feeds were updated correctly, processing data and sleeping {SLEEP_TIME} seconds")
      vehicles_output: dict = vehicles_to_json(vh, sh_trips, sh_routes, sh_stops, sh_stop_times, trips)
      stops_ouput: dict = arrival_times_to_json(vh, trips, sh_trips)
      path: str = SAVE_PATH_JSON + "/vehicles.json"
      with open(path, "w", encoding="utf-8") as output_file:
        json.dump(vehicles_output, output_file, ensure_ascii=False, indent=2)
      path = SAVE_PATH_JSON + '/arrival_times.json'
      with open(path, "w", encoding="utf-8") as output_file:
        json.dump(stops_ouput, output_file, ensure_ascii=False, indent=2)

      current = trips_feed_to_dict(trips)
      calculate_delays(current, previous_trip_feed, sh_stop_times, sh_trips, sqlitle_db, conn)
      previous_trip_feed = current

    if gtfs_scheduled_load_again >= COUNT_LOAD_GTFS_SCHEDULED_AGAIN:
      gtfs_scheduled_load_again = 0
      scheduled_collector()
      with open(SAVE_PATH_JSON + '/stops.json', 'r') as stops:
        sh_stops = json.load(stops)
      sh_trips = load_trips_by_id()
      sh_routes = load_routes_by_id()
      sh_stop_times = load_stop_times_by_trip()
      
    time.sleep(SLEEP_TIME)


if __name__ == "__main__":
  main()
