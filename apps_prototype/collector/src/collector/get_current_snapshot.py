import requests
from google.transit import gtfs_realtime_pb2
import time
from typing import Optional
import logging


def get_current_snapshot(
  s: requests.Session, 
  url: str,
  timeout: int,
) -> tuple[gtfs_realtime_pb2.FeedMessage, int]:
  """Fetch and parse the latest GTFS-RT feed snapshot."""
  r: requests.Response = s.get(url, timeout=timeout)
  r.raise_for_status()
  feed: gtfs_realtime_pb2.FeedMessage = gtfs_realtime_pb2.FeedMessage()
  feed.ParseFromString(r.content)   
  return feed, feed.header.timestamp

def retry_fetching(
  s: requests.Session,
  url: str,
  retries_left: int,
  lts: int,
  timeout: int,
  retry_delay_seconds: int,
  logger: logging.Logger,
  source: str = "",
) -> tuple[gtfs_realtime_pb2.FeedMessage, int, int]:
  """Retry fetching a feed until a newer timestamp appears or retries end."""
  if retries_left <= 0:
    raise ValueError("retries_left must be greater than 0")

  f: Optional[gtfs_realtime_pb2.FeedMessage] = None
  ts: int = lts

  time.sleep(retry_delay_seconds)
  for i in range(0, retries_left):
    logger.info(
      f"S=get_current_snapshot F=retry_fetching M=Retrying source={source} after {retry_delay_seconds} seconds"
    )
    retries_left -= 1
    try:
      f, ts = get_current_snapshot(s, url, timeout)
    except Exception as e:
      logger.warning(
        f"S=get_current_snapshot F=retry_fetching M=Error retrying source={source} E={e}"
      )
      raise e
    
    if ts > lts:
      break
    else:
      time.sleep(retry_delay_seconds)

  if f is None:
    raise RuntimeError("No snapshot could be fetched during retries")

  return f, ts, retries_left 

def obtain_last_snapshots(
  s: requests.Session,
  vh_previous_ts: int,
  trips_previous_ts: int,
  vehicle_positions_feed_url: str,
  trip_updates_feed_url: str,
  timeout: int,
  number_retries: int,
  retry_delay_seconds: int,
  logger: logging.Logger,
) -> tuple[
  Optional[gtfs_realtime_pb2.FeedMessage],
  int,
  Optional[gtfs_realtime_pb2.FeedMessage],
  int,
  int,
]:
  """Fetch latest vehicles and trips snapshots with bounded retry logic.

  return_status: 
  0 = Could not update vehicles 
  1 = Could update vehicles but not trips
  2 = Could update both feeds 
  """
  return_status: int = 0

  n_retries: int = number_retries

  try:
    vh_feed, vh_timestamp = get_current_snapshot(s, vehicle_positions_feed_url, timeout)
  except Exception as e:
    logger.warning(f"S=get_current_snapshot F=obtain_last_snapshots M=Error fetching vehicles feed E={e}")
    raise e

  if vh_timestamp <= vh_previous_ts:
    try:
      vh_feed, vh_timestamp, n_retries = \
                   retry_fetching(
                     s,
                     vehicle_positions_feed_url,
                     n_retries,
                     vh_previous_ts,
                     timeout,
                     retry_delay_seconds,
                     logger,
                     "vehicles",
                    )
    except Exception as e:
      logger.warning(
        f"S=get_current_snapshot F=obtain_last_snapshots M=Error retrying vehicles feed E={e}"
      )
      raise e

  if vh_timestamp <= vh_previous_ts:
    logger.warning("S=get_current_snapshot F=obtain_last_snapshots M=Could not update vehicles feed")
    return None, vh_previous_ts, None, trips_previous_ts, return_status
  
  return_status = 1

  try:
    trips_feed, trips_timestamp = get_current_snapshot(s, trip_updates_feed_url, timeout)
  except Exception as e:
    logger.warning(f"S=get_current_snapshot F=obtain_last_snapshots M=Error fetching trips feed E={e}")
    raise e

  if n_retries == 0:
    logger.warning(
      "S=get_current_snapshot F=obtain_last_snapshots M=Could not update trips feed because total retry time was done"
    )
    return vh_feed, vh_timestamp, None, trips_previous_ts, return_status
  
  if trips_timestamp <= trips_previous_ts:
    try:
      trips_feed, trips_timestamp, n_retries = \
                   retry_fetching(
                     s,
                     vehicle_positions_feed_url,
                     n_retries,
                     vh_previous_ts,
                     timeout,
                     retry_delay_seconds,
                     logger,
                     "trips",
                    )
    except Exception as e:
      logger.warning(
        f"S=get_current_snapshot F=obtain_last_snapshots M=Error retrying trips feed E={e}"
      )
      raise e

  if trips_timestamp <= trips_previous_ts:
    logger.warning("S=get_current_snapshot F=obtain_last_snapshots M=Could not update trips feed")
    return vh_feed, vh_timestamp, None, trips_previous_ts, return_status
  
  return_status = 2

  return vh_feed, vh_timestamp, trips_feed, trips_timestamp, return_status
