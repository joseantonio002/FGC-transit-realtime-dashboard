import requests
from google.transit import gtfs_realtime_pb2
import time
import asyncio

TRIP_UPDATES_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/trip-updates-gtfs_realtime/files/735985017f62fd33b2fe46e31ce53829"
VEHICLE_POSITIONS_FEED_URL: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/vehicle-positions-gtfs_realtime/files/d286964db2d107ecdb1344bf02f7b27b"
TEST_DURATION_SECONDS: int = 60 * 20
POLL_SECONDS: int = 10

def get_current_snapshot(
  s: requests.Session, 
  URL: str
) -> tuple[gtfs_realtime_pb2.FeedMessage, int]:
  r: requests.Response = s.get(URL, timeout=30)
  r.raise_for_status()
  feed: gtfs_realtime_pb2.FeedMessage = gtfs_realtime_pb2.FeedMessage()
  feed.ParseFromString(r.content)   
  return feed, feed.header.timestamp

def obtain_last_snapshots(
  s: requests.Session,
  trips_last_timestamp: int  
) -> tuple[gtfs_realtime_pb2.FeedMessage, gtfs_realtime_pb2.FeedMessage]:
  
  not_updated: bool = True
  while not_updated:
    feed, c_t = get_current_snapshot(s, TRIP_UPDATES_FEED_URL)
    if c_t <= trips_last_timestamp:
      print("Not updated yet")
      time.sleep(5)
      continue
    else:
      print(f"Updated, prev: {trips_last_timestamp}, current: {c_t}")
      not_updated = False

  return feed, c_t
    
    
def main():
  c_t: int = -1
  first_iteration: bool = True
  with requests.Session() as session:
    while True:
      f, c_t = obtain_last_snapshots(session, c_t)
      # The program does whatever it has to do
      # Once we have the two latest snapshots the rest is just simple operations
      # We know that data gets updated roughly every 100-115 seconds
      # So we sleep that amount of time, and all data sources should be updated

      # EDGE CASE: In we execute the script just before the data updates, we may skip
      # one snapshot. Solution, first snapshot does not count
      if first_iteration:
        first_iteration = False
      else:
        # Logic here
        pass
      time.sleep(120) 
  

def t():
  with requests.Session() as s:
    ft, tt = get_current_snapshot(s, TRIP_UPDATES_FEED_URL)
    t_ids = set()
    v_ids = set()
    print(ft.header)
    for trip in ft.entity:
      #print(trip.trip_update.trip.trip_id.strip())
      t_ids.add(trip.trip_update.trip.trip_id.strip())
      # convert each stop_time_update.arrival.time to human readable format
      #for stop_time_update in trip.trip_update.stop_time_update:
        #print(time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(stop_time_update.arrival.time)))

      if trip.trip_update.trip.trip_id.strip() == "625cdae61f726b11bb5d|602dc0e105":
        print(trip)


    print("-"*20)
    vt, tv = get_current_snapshot(s, VEHICLE_POSITIONS_FEED_URL)
    #print(vt.header)
    for vh in vt.entity:
      v_ids.add(vh.vehicle.trip.trip_id.strip())
      #print(vh)
      #print(time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(vh.vehicle.timestamp)))
      if vh.vehicle.trip.trip_id.strip() == "625cdae61f726b11bb5d|602dc0e105":
        print(vh)
    #print(v_ids)
    print("-"*20)
    #print(v_ids.difference(t_ids))
    #print(t_ids.difference(v_ids))
    dif = t_ids.difference(v_ids)
    #for trip in ft.entity:
      #if trip.trip_update.trip.trip_id.strip() in dif:
        #print(trip)

if __name__ == "__main__":
  #main()
  t()