import time
import requests
from load_gtfs_scheduled import load_routes_by_id, load_stop_times_by_trip, load_trips_by_id
from scheduled_collector import scheduled_collector, SAVE_PATH_VOLUME
from get_current_snapshot import obtain_last_snapshots
from gtfs_to_json import vehicles_to_json, arrival_times_to_json, trips_feed_to_dict
from calculate_delays import calculate_delays
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import sqlitle_functions
import sqlite3


TRIP_UPDATES_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/trip-updates-gtfs_realtime/files/735985017f62fd33b2fe46e31ce53829"
VEHICLE_POSITIONS_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/vehicle-positions-gtfs_realtime/files/d286964db2d107ecdb1344bf02f7b27b"
POLL_SECONDS: int = 10
TIMEOUT: int = 3

NUMBER_RETRIES: int = 10
RETRY_DELAY_SECONDS: int = 5
SLEEP_TIME: int = 90

COUNT_LOAD_GTFS_SCHEDULED_AGAIN: int = 200

DATABASE_PATH = SAVE_PATH_VOLUME + "/database.db"
LOG_PATH: Path = Path(__file__).resolve().parent / "collector.log"

def _build_logger() -> logging.Logger:
  """Create and configure the collector rotating file logger."""
  logger: logging.Logger = logging.getLogger("collector")
  if logger.handlers:
    return logger

  logger.setLevel(logging.INFO)
  handler: RotatingFileHandler = RotatingFileHandler(
    LOG_PATH,
    maxBytes=800_000,
    backupCount=3,
    encoding="utf-8",
  )
  formatter: logging.Formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(message)s"
  )
  handler.setFormatter(formatter)
  logger.addHandler(handler)
  logger.propagate = False
  return logger


def new_session() -> requests.Session:
  """Create a new HTTP session."""
  s: requests.Session = requests.Session()
  return s


def backoff(backoff_counter: int, logger: logging.Logger) -> None:
  """Sleep using exponential backoff after repeated failures."""
  logger.warning(
    "S=collector F=backoff M=Exponential backoff activated "
    f"{backoff_counter} times in a row, sleeping for 2^{backoff_counter} seconds"
  )
  time.sleep(2 ** backoff_counter)


def main() -> None:
  """Continuously fetch newest vehicles and trip snapshots."""
  logger: logging.Logger = _build_logger()
  s: requests.Session = new_session()
  trips_current_ts: int = -1
  vh_current_ts: int = -1
  backoff_counter: int = 0

  conn: sqlite3.Connection = sqlite3.connect(DATABASE_PATH)
  sqlitle_db: sqlite3.Cursor = conn.cursor()
  sqlitle_functions.create_historic_table(sqlitle_db, conn)
  
  scheduled_collector()
  gtfs_scheduled_load_again: int = 0
  with open(SAVE_PATH_VOLUME + '/stops.json', 'r') as stops:
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
        logger=logger,
      )
    except requests.exceptions.HTTPError as e:
      status: int = e.response.status_code
      logger.warning(
        f"S=collector F=main M=HTTP error while fetching snapshots status={status} E={e}"
      )
      backoff_counter += 1
      backoff(backoff_counter, logger)
      continue
    except requests.exceptions.ConnectionError as e:
      logger.warning(
        f"S=collector F=main M=Connection error while fetching snapshots, resetting session E={e}"
      )
      s.close()
      s = new_session()
      backoff_counter += 1
      backoff(backoff_counter, logger)
      continue
    except requests.exceptions.ReadTimeout as e:
      logger.warning(f"S=collector F=main M=Timeout while fetching snapshots E={e}")
      backoff_counter += 1
      backoff(backoff_counter, logger)
      continue
    except requests.exceptions.RequestException as e:
      logger.warning(f"S=collector F=main M=Request exception while fetching snapshots E={e}")
      backoff_counter += 1
      backoff(backoff_counter, logger)
      continue
    except Exception as e:
      logger.warning(f"S=collector F=main M=Unexpected error while fetching snapshots E={e}")
      backoff_counter += 1
      backoff(backoff_counter, logger)
      continue

    backoff_counter = 0
    gtfs_scheduled_load_again += 1

    if return_status == 0:
      logger.info("S=collector F=main M=Skipping execution because vehicles was not updated")
    elif return_status == 1:
      logger.info("S=collector F=main M=Vehicles was updated but trips not, skipping execution")
    else:
      logger.info(
        f"S=collector F=main M=Both feeds were updated correctly, processing data and sleeping {SLEEP_TIME} seconds"
      )
      try:
        vehicles_output: dict = vehicles_to_json(
          vh,
          sh_trips,
          sh_routes,
          sh_stops,
          sh_stop_times,
          trips,
          logger,
        )
      except Exception as e:
        logger.warning(f"S=collector F=main M=Error converting vehicles feed to JSON E={e}")
        time.sleep(SLEEP_TIME)
        continue

      try:
        stops_ouput: dict = arrival_times_to_json(vh, trips, sh_trips, sh_routes)
      except Exception as e:
        logger.warning(f"S=collector F=main M=Error converting arrival times feed to JSON E={e}")
        time.sleep(SLEEP_TIME)
        continue

      try:
        path: str = SAVE_PATH_VOLUME + "/vehicles.json"
        with open(path, "w", encoding="utf-8") as output_file:
          json.dump(vehicles_output, output_file, ensure_ascii=False, indent=2)
        path = SAVE_PATH_VOLUME + '/arrival_times.json'
        with open(path, "w", encoding="utf-8") as output_file:
          json.dump(stops_ouput, output_file, ensure_ascii=False, indent=2)
      except Exception as e:
        logger.warning(f"S=collector F=main M=Error writing output JSON files E={e}")
        time.sleep(SLEEP_TIME)
        continue

      try:
        current = trips_feed_to_dict(trips)
      except Exception as e:
        logger.warning(f"S=collector F=main M=Error converting trips feed to dict E={e}")
        time.sleep(SLEEP_TIME)
        continue

      try:
        calculate_delays(current, previous_trip_feed, sh_stop_times, sh_trips, sqlitle_db, conn, logger)
      except Exception as e:
        logger.warning(f"S=collector F=main M=Error calculating delays from trip feeds E={e}")
        time.sleep(SLEEP_TIME)
        continue

      previous_trip_feed = current

      try:
        if gtfs_scheduled_load_again >= COUNT_LOAD_GTFS_SCHEDULED_AGAIN:
          gtfs_scheduled_load_again = 0
          scheduled_collector()
          with open(SAVE_PATH_VOLUME + '/stops.json', 'r') as stops:
            sh_stops = json.load(stops)
          sh_trips = load_trips_by_id()
          sh_routes = load_routes_by_id()
          sh_stop_times = load_stop_times_by_trip()
      except Exception as e:
        logger.warning(f"S=collector F=main M=Error reloading scheduled GTFS artifacts E={e}")
        time.sleep(SLEEP_TIME)
        continue
    
    time.sleep(SLEEP_TIME)


if __name__ == "__main__":
  main()
