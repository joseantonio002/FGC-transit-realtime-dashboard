import requests
from google.transit import gtfs_realtime_pb2
import time

TRIP_UPDATES_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/trip-updates-gtfs_realtime/files/735985017f62fd33b2fe46e31ce53829"
VEHICLE_POSITIONS_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/vehicle-positions-gtfs_realtime/files/d286964db2d107ecdb1344bf02f7b27b"
POLL_SECONDS: int = 10
TIMEOUT: int = 3

NUMBER_RETRIES: int = 10
RETRY_DELAY_SECONDS: int = 5 # 5 * 10 = 50 seconds 
SLEEP_TIME: int = 100 

def new_session():
    s = requests.Session()
    return s

def get_current_snapshot(
  s: requests.Session, 
  URL: str
) -> tuple[gtfs_realtime_pb2.FeedMessage, int]:
  r: requests.Response = s.get(URL, timeout=TIMEOUT)
  r.raise_for_status()
  feed: gtfs_realtime_pb2.FeedMessage = gtfs_realtime_pb2.FeedMessage()
  feed.ParseFromString(r.content)   
  return feed, feed.header.timestamp

def retry_fetching(s: requests.Session, URL: str, retries_left: int, lts: int, source: str=""):

  time.sleep(RETRY_DELAY_SECONDS)
  for i in range(0, retries_left):
    print(f"Retrying to fetch {source} after {RETRY_DELAY_SECONDS} seconds...")
    retries_left -= 1
    try:
      f, ts = get_current_snapshot(s, URL)
    except Exception as e:
      print("Error trying to retry fetch")
      raise e
    
    if ts > lts:
      break
    else:
      time.sleep(RETRY_DELAY_SECONDS)

  return f, ts, retries_left 

def obtain_last_snapshots(
  s: requests.Session,
  vh_previous_ts: int,
  trips_previous_ts: int 
) -> tuple[gtfs_realtime_pb2.FeedMessage, gtfs_realtime_pb2.FeedMessage]:
  
  """
  return_status: 
  0 = Could not update vehicles 
  1 = Could update vehicles but not trips
  2 = Could update both feeds 
  """
  return_status: int = 0

  n_retries: int = NUMBER_RETRIES

  try:
    vh_feed, vh_timestamp = get_current_snapshot(s, VEHICLE_POSITIONS_FEED_URL)
  except Exception as e:
    print("Error fetching vehicles feed")
    raise e

  if vh_timestamp <= vh_previous_ts:
    try:
      vh_feed, vh_timestamp, n_retries = \
                   retry_fetching(s, VEHICLE_POSITIONS_FEED_URL, n_retries, vh_previous_ts, "vehicles")
    except Exception as e:
      print("Error retrying to fetch vehicles feed")
      raise e

  if vh_timestamp <= vh_previous_ts:
    print("Could not update vehicles feed")
    return None, vh_previous_ts, None, trips_previous_ts, return_status
  
  return_status = 1

  try:
    trips_feed, trips_timestamp = get_current_snapshot(s, TRIP_UPDATES_FEED_URL)
  except Exception as e:
    print("Error fetching trips feed")
    raise e
  
  if n_retries == 0:
    print("Could not update trips feed because total retry time was done")
    return vh_feed, vh_timestamp, None, trips_previous_ts, return_status
  
  if trips_timestamp <= trips_previous_ts:
    try:
      trips_feed, trips_timestamp, n_retries = \
                   retry_fetching(s, VEHICLE_POSITIONS_FEED_URL, n_retries, vh_previous_ts, "trips")
    except Exception as e:
      print("Error retrying to fetch trips feed")
      raise e
    
  if trips_timestamp <= trips_previous_ts:
    print("Could not update trips feed")
    return vh_feed, vh_timestamp, None, trips_previous_ts, return_status
  
  return_status = 2

  return vh_feed, vh_timestamp, trips_feed, trips_timestamp, return_status

def backoff(backoff_counter):
  print(f"Exponential backoff activated {backoff_counter} times in a row, sleeping for 2^{backoff_counter} seconds")
  time.sleep(2 ** backoff_counter)

def main():
  s = new_session()
  trips_current_ts = -1
  vh_current_ts = -1
  backoff_counter = 0
  while True:
    try:
      vh, vh_current_ts, trips, trips_current_ts, return_status = \
                          obtain_last_snapshots(s, vh_current_ts, trips_current_ts)
    except requests.exceptions.HTTPError as e:
      status: int = e.response.status_code
      print(f"HTTP Error fetching data: {status}")
      backoff_counter += 1
      backoff(backoff_counter)
      continue
    except requests.exceptions.ConnectionError as e:
      # Reset only on connection-level failure
      print("Connection error, reseting connection")
      s.close()
      s = new_session()
      backoff_counter += 1
      backoff(backoff_counter)
      continue
    except requests.exceptions.ReadTimeout as errrt:
      print("Time out")
      backoff_counter += 1
      backoff(backoff_counter)
      continue
    except requests.exceptions.RequestException as errex:
      print("Exception request")
      raise errex
    backoff_counter = 0 

    if return_status == 0:
      print("Skipping execution because vehicles was not updated")
    elif return_status == 1:
      print("Vehicles was updated but trips not")
      print(vh.entity[0])
    else:
      print("Both feeds were updated correctly")
      print(vh.entity[0])
      print(trips.entity[0])
    time.sleep(SLEEP_TIME)



if __name__ == "__main__":
  main()