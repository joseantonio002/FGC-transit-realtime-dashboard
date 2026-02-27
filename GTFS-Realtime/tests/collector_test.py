import requests
from google.transit import gtfs_realtime_pb2
import time
import asyncio

TRIP_UPDATES_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/trip-updates-gtfs_realtime/files/735985017f62fd33b2fe46e31ce53829"
VEHICLE_POSITIONS_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/vehicle-positions-gtfs_realtime/files/d286964db2d107ecdb1344bf02f7b27b"
POLL_SECONDS: int = 10

NUMBER_RETRIES: int = 10
RETRY_DELAY_SECONDS: int = 5 # 5 * 10 = 50 seconds  

def new_session():
    s = requests.Session()
    return s

def get_current_snapshot(
  s: requests.Session, 
  URL: str
) -> tuple[gtfs_realtime_pb2.FeedMessage, int]:
  r: requests.Response = s.get(URL, timeout=3)
  r.raise_for_status()
  #mock = requests.Response()
  #mock.status_code = 429
  #raise requests.exceptions.HTTPError(response=mock)
  feed: gtfs_realtime_pb2.FeedMessage = gtfs_realtime_pb2.FeedMessage()
  feed.ParseFromString(r.content)   
  return feed, feed.header.timestamp

def obtain_last_snapshots(
  s: requests.Session,
  vh_current_ts: int,
  trips_current_ts: int 
) -> tuple[gtfs_realtime_pb2.FeedMessage, gtfs_realtime_pb2.FeedMessage]:
  
  try:
    vh_feed, vh_timestamp = get_current_snapshot(s, VEHICLE_POSITIONS_FEED_URL)
  except Exception as e:
    print("Error fetching vehicles feed")
    raise e


  
  try:
    trips_feed, trips_timestmap = get_current_snapshot(s, TRIP_UPDATES_FEED_URL)
  except Exception as e:
    print("Error fetching trips feed")
    raise e


  return vh_feed, vh_timestamp, trips_feed, trips_timestmap


def main():
  s = new_session()
  trips_current_ts = -1
  vh_current_ts = -1
  backoff_counter = 0
  while True:
    try:
      vh, vh_current_ts, trips, trips_current_ts = \
                          obtain_last_snapshots(s, vh_current_ts, trips_current_ts)
    except requests.exceptions.HTTPError as e:
      status: int = e.response.status_code
      print(f"HTTP Error fetching data: {status}")
      backoff_counter += 1
      print(f"Exponential backoff activated {backoff_counter} times in a row, sleeping for 2^{backoff_counter} seconds")
      time.sleep(2 ** backoff_counter)
      continue
    except requests.exceptions.ConnectionError as e:
      # Reset only on connection-level failure
      print("Connection error, reseting connection")
      s.close()
      s = new_session()
      backoff_counter += 1
      print(f"Exponential backoff activated {backoff_counter} times in a row, sleeping for 2^{backoff_counter} seconds")
      time.sleep(2 ** backoff_counter)
      continue
    except requests.exceptions.ReadTimeout as errrt:
      print("Time out")
      backoff_counter += 1
      print(f"Exponential backoff activated {backoff_counter} times in a row, sleeping for 2^{backoff_counter} seconds")
      time.sleep(2 ** backoff_counter)
      continue
    except requests.exceptions.RequestException as errex:
      print("Exception request")
      raise errex
    backoff_counter = 0 
    print(vh.entity[0], trips.entity[0])
    time.sleep(100)



if __name__ == "__main__":
  main()