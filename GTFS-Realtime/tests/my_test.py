import requests
from google.transit import gtfs_realtime_pb2
from time import sleep
import asyncio

TRIP_UPDATES_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/trip-updates-gtfs_realtime/files/735985017f62fd33b2fe46e31ce53829"
VEHICLE_POSITIONS_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/vehicle-positions-gtfs_realtime/files/d286964db2d107ecdb1344bf02f7b27b"
TEST_DURATION_SECONDS: int = 60 * 20
POLL_SECONDS: int = 10



"""
  r: requests.Response = requests.get(TRIP_UPDATES_FEED_URL)
  r.raise_for_status()
  feed: gtfs_realtime_pb2.FeedMessage = gtfs_realtime_pb2.FeedMessage()
  feed.ParseFromString(r.content)
"""


def obtain_last_snapshots(s: requests.Session, vlt, tlt) -> tuple[gtfs_realtime_pb2.FeedMessage, gtfs_realtime_pb2.FeedMessage]:
  
  def get_current_snapshot(
    s: requests.Session, 
    URL: str
  ) -> tuple[gtfs_realtime_pb2.FeedMessage, int]:
    r: requests.Response = s.get(URL, timeout=30)
    r.raise_for_status()
    feed: gtfs_realtime_pb2.FeedMessage = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(r.content)   
    return feed, feed.header.timestamp
  
  not_updated: bool = True
  while not_updated:
    feed, c_t = get_current_snapshot(s, TRIP_UPDATES_FEED_URL)
    if c_t <= tlt:
      print("Not updated yet")
      sleep(20)
      continue
    else:
      print(f"Updated, prev: {tlt}, current: {c_t}")
      not_updated = False


  return feed, c_t
    
    
def main():
  vehicles_last_timestamp = -1
  trips_last_timestamp = -1
  with requests.Session() as session:
    while True:
      f, trips_last_timestamp = obtain_last_snapshots(session, vehicles_last_timestamp, trips_last_timestamp)
      sleep(30)
  

  
  
  



if __name__ == "__main__":
  main()