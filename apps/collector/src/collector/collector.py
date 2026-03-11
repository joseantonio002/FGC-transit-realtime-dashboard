import time
import requests
from get_current_snapshot import obtain_last_snapshots

TRIP_UPDATES_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/trip-updates-gtfs_realtime/files/735985017f62fd33b2fe46e31ce53829"
VEHICLE_POSITIONS_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/vehicle-positions-gtfs_realtime/files/d286964db2d107ecdb1344bf02f7b27b"
POLL_SECONDS: int = 10
TIMEOUT: int = 3

NUMBER_RETRIES: int = 10
RETRY_DELAY_SECONDS: int = 5
SLEEP_TIME: int = 100


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

    backoff_counter = 0

    if return_status == 0:
      print("Skipping execution because vehicles was not updated")
    elif return_status == 1:
      print("Vehicles was updated but trips not")
      print(vh.entity[0])
    else:
      print(f"Both feeds were updated correctly, processing data and sleeping {SLEEP_TIME} seconds")
      print(vh.entity[0])
      print(trips.entity[0])

    time.sleep(SLEEP_TIME)


if __name__ == "__main__":
  main()
