# 01/02/2026

Created a prototype just to see the components I need

# 03/02/2026

Lets make a log file to track how the project evolves

The objective is to build a data pipeline like the one I did in air_transport_statistics but this time making it scalable and truly autonomous by hosting it in the cloud, and making an API to the data so we can do lazy fetching instead of loading it all at once like we did in the previous project

Possible data source: [Eurostat](https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access)

Since I haven't done an API in some time, first thing I'm going to do is review some backend theory. Once I've done that, I will study what options I have to host the page the cheapest way possible. So the plan for now is:

1. Review backend theory and API's
2. Check hosting options
3. Find a data source that updates regularly and I can retrieve
4. Development

# 05/02/2026

Security concerns for my API:

1. Publish the API in HTTPS not HTTP
2. CORS
3. Rate Limiting
4. Prevent SQL Injection, validate parameters
5. Make sure to not push passwords, DB conection keys...

Possible hosts:

- Shared hosting
- VPS (managed and unmanaged)
- Platform as a Service / PaaS
- Cloud Virtual Machines / IaaS
- Dedicated Server

For my case I would prob need shared hosting, unmanaged VPS or try host in github and use
the free tiers in Render, Railway, or Fly.io. They have free plans that "sleep" when not in use.
Tomorrow I will check and decide on one of them


# 06/02/2026

Its between [hetzner](https://www.hetzner.com/cloud/), [ionos](https://www.ionos.es/servidores/vps) and [contabo](https://contabo.com/es/vps/?utm_source=google&utm_medium=cpc&utm_campaign=brand-europe-es-eur&utm_term=generic&utm_content=contabo&gad_source=1&gad_campaignid=22529964914&gbraid=0AAAAAD_Qy-cdMpRvXJEJR0SDbQ835B9pu&gclid=CjwKCAiAv5bMBhAIEiwAqP9GuCMPRzA0dNFWWV5_LPaZbfzY6a-5XA9Iu3cRu7lk-DWj2WMO0Li5whoC7ZQQAvD_BwE).
I also have to check how to get the SSL certificate for free

# 10/02/2026

I will probably choose hetzner and use it for other things like trying openclaw.
So know that I know the basics, I'm going to start the develpment in my local environment for now to get this thing going and leave the cloud for later

First thing is to find some data to work with, lets explore...

# 11/02/2026

Thinking about either: 

- GTFS data (I have to decide schedule or realtime)
- Wheather and planes opendata

Final idea, after spending the whole afternoon checking posible data sources and thinking what I could show, I decided to use GTFS schedule data from [TITSA](https://nap.transportes.gob.es/Files/Detail/1130) and visualize routes in the map and the delay for each stop, in the last few days (using the latest GTFS data) and overall (stored data from previous days).


# 12/02/2026

I thought that this [TITSA](https://nap.transportes.gob.es/Files/Detail/1130) dataset contained real data from trips operated, but I'm starting to suspect is just the planned trips, instead of the completed ones. Lets explore ```trips.txt``` with duckdb to see if it contains future trips, in that case I will know for certain are just planned trips not completed ones.

```
┌──────────┬────────────┬─────────┬────────────────┬──────────┬────────────┬──────────┬────────────────┬────────────┐
│ route_id │ service_id │ trip_id │ trip_headsign  │ shape_id │ service_id │   date   │ exception_type │ real_date  │
│  int64   │   int64    │  int64  │    varchar     │  int64   │   int64    │  int64   │     int64      │    date    │
├──────────┼────────────┼─────────┼────────────────┼──────────┼────────────┼──────────┼────────────────┼────────────┤
│       13 │          1 │       1 │ LA MATANZA (T) │        1 │          1 │ 20260810 │              1 │ 2026-08-10 │
│       13 │          1 │       2 │ LA MATANZA (T) │        1 │          1 │ 20260810 │              1 │ 2026-08-10 │
│       13 │          1 │       3 │ LA MATANZA (T) │        1 │          1 │ 20260810 │              1 │ 2026-08-10 │
│       13 │          1 │       4 │ LA MATANZA (T) │        1 │          1 │ 20260810 │              1 │ 2026-08-10 │
│       13 │          1 │       5 │ LA MATANZA (T) │        1 │          1 │ 20260810 │              1 │ 2026-08-10 │

```

Indeed, these are planned trips, not completed trips.

> GTFS Schedule contains information about routes, schedules, fares, and geographic transit details among many other features, and it is presented in simple text files. This straightforward format allows for easy creation and maintenance without relying on complex or proprietary software.

So turns out I was wrong, I have to search some other data source, either GTFS Realtime or a completely different thing. GTFS Schedule is, like its name states, for schedules/planned trips, not completed ones. 

Understanding GTFS-Realtime

- GTFS-Realtime vehicle positions are usually served as a protobuf binary (FeedMessage), not plain JSON.
- Your OpenDataSoft dataset (vehicle-positions-gtfs_realtime) does not directly expose rows like “one row per vehicle.”
- Instead, OpenDataSoft exposes a record containing a file pointer:
  - file.id
  - file.url
  - file.filename (in this case vehicleposition.pb)
- The actual vehicle data is inside that protobuf file at file.url.
So the data flow is:
1. Query metadata endpoint (JSON).
2. Extract file.url.
3. Download .pb.
4. Parse GTFS-RT protobuf.
5. Read feed.header + feed.entity[*].vehicle

### What is Protocol Buffers (Protobuf)?

* Protocol Buffers (protobuf) is a binary serialization format created by Google.
* It is used to efficiently encode structured data.
* It is:

  * Smaller than JSON
  * Faster to parse
  * Strongly typed
  * Schema-based

Unlike JSON or CSV:

* Protobuf is **not human-readable**
* It requires a `.proto` schema definition to decode

In GTFS-Realtime:

* The schema is defined in `gtfs-realtime.proto`
* The top-level message is `FeedMessage`

---

### What is a Protobuf Binary (FeedMessage)?

When a GTFS-Realtime feed is downloaded:

* The server returns raw binary bytes (`.pb` file)
* Those bytes represent a serialized `FeedMessage`
* The structure typically is:

```
FeedMessage
 ├── header
 └── entity[] (list of FeedEntity)
```

Each `entity` may contain:

* vehicle (VehiclePosition)
* trip_update (TripUpdate)
* alert (Alert)

The script parses it with:

```python
feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(file_bytes)
```

This:

* Creates a new empty message object
* Decodes the binary into structured fields
* Makes it accessible as normal Python attributes

Important:

* The schema is loaded once when importing `gtfs_realtime_pb2`
* `FeedMessage()` just creates a new container object
* Creating a new instance per snapshot is correct and inexpensive

---

## About `gtfs_realtime_pb2.FeedMessage()`

* The schema is already compiled into Python classes at import time.
* `FeedMessage()` does **not reload the schema**.
* It simply creates a new empty message instance.
* `ParseFromString()` fills that instance with decoded data.
* Creating a new object for each feed download is correct and safe.
* Reusing the same object offers no meaningful performance gain.

Key idea:

* Schema = loaded once at import.
* `FeedMessage()` = new container for one snapshot.

---

## About `requests.Session()`

* `requests.Session()` enables HTTP connection reuse (connection pooling).
* Without it, each `requests.get()`:

  * Opens a new TCP connection
  * Performs TLS handshake
  * Sends request
  * Closes connection
* With a session:

  * Connections are reused
  * Polling is more efficient
  * Less latency and overhead

In this script:

* Metadata endpoint is polled
* Protobuf file is downloaded
* Repeated every few seconds

Using `Session` is correct for repeated HTTP calls.

Key idea:

* `Session` manages persistent HTTP connections.
* It improves efficiency for [polling APIs](https://medium.com/@sankalpa115/what-is-polling-b1ff70e87001) like GTFS-Realtime.

### Entities in each data source

1) vehicle position:

```
id: "0"
vehicle {
  trip {
    trip_id: "6c4bdaeb02747640fd55c10d40|6a2dc5e50b"
    schedule_relationship: SCHEDULED
  }
  position {
    latitude: 41.5613556
    longitude: 2.0175519
  }
  current_status: IN_TRANSIT_TO
  timestamp: 1770913924
  stop_id: "VP"
  vehicle {
    id: "1f2cc5fd0075"
  }
  occupancy_status: FEW_SEATS_AVAILABLE
}
```

2) trip updates:

```
id: "S|20260212|625cdae1027438|622dc6e702"
trip_update {
  trip {
    trip_id: "625cdae1027438|622dc6e702"
    start_date: "20260212"
  }
  stop_time_update {
    arrival {
      time: 1770914630
    }
    departure {
      time: 1770914660
    }
    stop_id: "SP2"
  }
  stop_time_update {
    arrival {
      time: 1770914750
    }
    departure {
      time: 1770914780
    }
    stop_id: "GO2"
  }
  stop_time_update {
    arrival {
      time: 1770914855
    }
    departure {
      time: 1770914885
    }
    stop_id: "EU2"
  }
  stop_time_update {
    arrival {
      time: 1770914960
    }
    departure {
      time: 1770914990
    }
    stop_id: "IC2"
  }
  stop_time_update {
    arrival {
      time: 1770915080
    }
    departure {
      time: 1770915110
    }
    stop_id: "MG2"
  }
  stop_time_update {
    arrival {
      time: 1770915230
    }
    departure {
      time: 1770915230
    }
    stop_id: "PE3"
  }
  timestamp: 1770914630
}

```

3) service alerts

```
id: "OBSERVATIONS_M0123_IC"
alert {
  active_period {
    start: 1770861700
    end: 1770948000
  }
  informed_entity {
    trip {
      trip_id: "625cdae1027438|632dc6e101"
      start_date: "20260212"
    }
    stop_id: "IC"
  }
  cause: UNKNOWN_CAUSE
  effect: UNKNOWN_EFFECT
  header_text {
    translation {
      text: "Enllaç amb autobús amb destinació Igualada"
    }
  }
}
```

### Similar project

I realized, maybe there is already a project that takes this data to do something similar, after searching a little I came across with [geotren](https://geotren.fgc.cat/) is made by FGC (the train company that provides the GTFS data) and it shows in real time where the trains are in a map and the stops. My idea would be to do something similar but adding the historic of delays, or some filters.

What this page does is:

- Poll https://geotren.fgc.cat/tracker/trens.geojson every ~4 seconds
- Render points on Google Maps markers
- Load static line geometry from GeoJSON files
- No obvious WebSocket/SSE push in client code

This pages uses a gejson file, maybe I can use it too instead of the GTFS Realtime. Possible [data source](https://datos.gob.es/es/catalogo/a09002970-fgc-posicionamiento-de-los-trenes-_geotren)

To add a [google map](https://developers.google.com/maps/documentation/javascript/add-google-map) to your page, however is not fully free (check this more in detail later).

- Google Maps JavaScript API requires an API key and a billing-enabled Google Cloud project.
- You usually get a monthly free credit/quota, but after that usage is paid (pricing depends on map loads and APIs used).
- Even within free quota, you must follow Google Maps Platform Terms (attribution, usage limits, etc.).
- So you can replicate it technically, but for production you should assume potential cost.
If you want a lower-cost/open option, use:
- Leaflet or MapLibre + OpenStreetMap-compatible tiles (or your own tiles),
- but still check that tile provider’s usage policy (many “free” tiles disallow heavy production traffic).
If you want, I can suggest the best stack for your expected traffic (small demo vs production).

[GTFS Scheduled](https://dadesobertes.fgc.cat/explore/dataset/gtfs_zip/table/) and [line dimension](https://dadesobertes.fgc.cat/explore/dataset/lineas-red-fgc/table/)


# 13/02/2026

- Whats the difference between the geojson and GTFS data?
- Can I query the geojson indefinitely

After asking the AI:

- GTFS Static is scheduled data (routes, stops, trips, timetables) in .txt files.
- GTFS-Realtime is live operational updates (vehicle positions, delays, alerts) in protobuf (.pb) format.
- GeoJSON is just a geospatial JSON format used to draw things on maps (points/lines/polygons).

So in GeoTren-like systems, they often do:
- backend ingests GTFS-RT (protobuf),
- backend transforms it into simpler GeoJSON for the browser,
- browser polls that GeoJSON and renders markers quickly.

About querying trens.geojson “without restrictions”:
- Technically it may be publicly reachable with no auth.
- Legally/operationally, that does not mean unrestricted use.
- You still must respect:
  - provider terms/license,
  - fair-use/rate limits (even if not documented),
  - attribution/redistribution rules,
  - no abusive polling/scraping.

In conclusion, im going to use the GTFS-Realtime to build my own GeoJSON or whatever other method I come up with. Lets not use their geojson.

Okay, so I'm going to use GTFS-Realtime, lets check out the GTFS Scheduled data.

Lucky for us, is exactly the same as the GTFS data from TITSA. So we have the planned trips for this year.

[Data definition](https://gtfs.org/documentation/realtime/reference/) for vehicle position, trip updates and service alerts.

So the final idea is:

![prototype](./prototype_img.png)

- web page with:
  - A map with the trains in real time and the stops (like the one in geotrain) 
    - If you click in a train it shows you info in real time, historic delay data and number of service alerts from that route
    - Also 
    - The same with the stops
  - Filters for route and stops showing in the map
    - Filter to select what routes display
    - Filter that takes you to a stop, if you click it, the map goes to that stop
  - Historical data about most delayed routes and stops with most delays and average time of that delays. Or other data. But the main point is to show aggregated historical data.

To obtain delay data we need to compare GTFS Scheduled with GTFS Realtime data.

Next day think about the architecture and how we are going to run this.

# 14/02/2026

![firstv](./firstv.png)


Architecture idea (similar to GeoTren, but using GTFS-Realtime as the source):

- A **collector process** polls the GTFS-Realtime feeds every few seconds (protobuf), parses them, and materializes the *latest* state into a `vehicles.geojson` snapshot on disk.
  - Writing a single snapshot file keeps the realtime path cheap for the map (no DB query per refresh).
  - The snapshot should be written atomically (write to `*.tmp` and rename) so the API never serves a half-written file.
- The same collector also stores **historical observations** into a database (initially SQLite).
  - The frontend loads this historical/aggregate data once on page load (or on demand), instead of re-querying it every few seconds.
  - This reduces read/write contention and avoids “DB as a realtime cache”.
  - If using SQLite, enable **WAL mode** so reads can proceed while the collector is writing.
- The backend exposes two endpoints:
  - `GET /api/vehicles.geojson` -> serves the latest snapshot for realtime map updates.
  - `GET /api/stats` (or similar) -> serves historical/aggregate data from the database.

Frontend hosting: serve the static UI with GitHub Pages, and host the collector + API on a VPS (CORS + HTTPS required). That keeps the frontend deployment simple while the backend can run continuously.

# 17/02/2026 - 18/02/2026

We have the architecture, we can start developing the plan I have in mind is:

1. Start developing the collector locally, first really understand how the data looks and how I'm going to process and transform it. Then code it and test. This is the main part.
2. Once I have that, buy the VPS and try it there
3. Make the frontend and API.

## Starting STEP 1

The following protocol buffer data types are used to describe feed elements:

message: Complex type\
enum: List of fixed values

This is the structure of GTFS Realtime:

```
FeedMessage
  FeedHeader
    Incrementality

  FeedEntity
    TripUpdate
      TripDescriptor
        ScheduleRelationship
      VehicleDescriptor
        WheelchairAccessible
      StopTimeUpdate
        StopTimeEvent
        ScheduleRelationship
        StopTimeProperties
      TripProperties

    VehiclePosition
      TripDescriptor
        ScheduleRelationship
        ModifiedTripSelector
      VehicleDescriptor
        WheelchairAccessible
      Position
      VehicleStopStatus
      CongestionLevel
      OccupancyStatus
      CarriageDetails

    Alert
      TimeRange
      EntitySelector
        TripDescriptor
          ScheduleRelationship
      Cause
      Effect
      TranslatedString
        Translation
      SeverityLevel

    Shape

    Stop
      WheelchairBoarding

    TripModifications
      Modification
        ReplacementStop

```

As we can see, we have six types of feed entities, in this case we only care about FeedEntity, VehiclePosition and Alert because these are the ones that are provided to us.

After learning about the realtime data, the final idea is this:

### 1) To create the Geoson we only need the last data we retrieve

Turns out the pb file is always the same, to check updates we need to check the header timestamp from the protobuff



### 2) For historical data, create the following table:

```
┌─────────┬──────────┬─────────┬───────────────┬─────────────────────┬───────────────────┬─────────────────┬─────────────────────┬───────────────────┬──────────────────┬─────────────┬─────────────────────┐
│ trip_id │ route_id │ stop_id │ stop_sequence │   arrival_planned   │    arrival_real   │ arrival_delay   │  departure_planned  │   departure_real  │ departure_delay  │ data_source │   event_timestamp   │
│  varchar  │  varchar   │  varchar  │     int64     │      timestamp      │     timestamp     │     int64       │      timestamp      │     timestamp     │      int64       │   varchar   │      timestamp      │
├─────────┼──────────┼─────────┼───────────────┼─────────────────────┼───────────────────┼─────────────────┼─────────────────────┼───────────────────┼──────────────────┼─────────────┼─────────────────────┤

```

Here we store every time we detect an arrival and departure using trips updates and vehicle position. We could also have only three columns for the two times and delay, and add a column movement_type that takes value departure and arrival.

**VehiclePosition = “Where is the vehicle right now and what stop is it associated with.”**

It typically updates **very frequently** (every 1–30 seconds, depends on agency).

What it holds (in practice):

* `position.lat/lon`: current GPS
* `timestamp`: when that GPS/status was measured (Unix UTC)
* `trip.trip_id`: what trip the system thinks it’s serving (sometimes missing or wrong)
* `stop_id` + `current_status`: where it is relative to *a stop*

  * `IN_TRANSIT_TO`: traveling to `stop_id` (the next stop)
  * `INCOMING_AT`: very close, about to arrive at `stop_id`
  * `STOPPED_AT`: currently stopped at `stop_id`

**Important limitation:** VehiclePosition usually **does not give you actual arrival/departure times**. It gives you a state snapshot. If you try to infer stop times from it, you’re building your own event detector (state transitions + heuristics).

#### Can you derive “actual arrival/departure” from VehiclePosition?

Yes, but it’s approximate:

* **arrival_time_actual(stop)** ≈ first time you observe `current_status = STOPPED_AT` for that `stop_id`
* **departure_time_actual(stop)** ≈ first time after that where status changes to `IN_TRANSIT_TO` (and stop_id becomes next stop) or STOPPED_AT disappears

But this is noisy because:

* updates may skip states (you might never see `INCOMING_AT`)
* sampling frequency affects precision
* `stop_id` may be “next stop” not “current stop” depending on agency interpretation if `current_stop_sequence` is missing
* vehicles can dwell, reverse, lose GPS, etc.

So: **VehiclePosition is best for maps and “where is it now.”** Not ideal as your primary punctuality truth.

---

**TripUpdate = “For this trip, here are arrival/departure times (predicted and sometimes actual) for stops.”**

It usually updates **less frequently than VehiclePosition**, but it’s the right feed for stop timing.

#### Are these “actual” or “predicted”?

GTFS-RT allows both, but many agencies **do not explicitly label actual vs predicted**. The usual behavior is:

* For stops in the future: `time` is a prediction
* For a stop that just happened: `time` may become “actual” (sometimes uncertainty becomes 0, but not always provided)
* Some feeds keep updating past stops; others drop past stops quickly

So for analytics you treat TripUpdate times as **best available estimate**, and if you need strict “actual arrival,” you’ll only be certain if the feed provider clearly makes them measured values (rarely explicit).

---

#### **TripUpdate** as main comparison to `stop_times.txt`.

Because `stop_times` is stop-level schedule, and TripUpdate is stop-level RT timing.

* Important, `stop_times` times are service day times:
  * static stop_times are “service-day times” like `25:10:00`
  * RT gives absolute epoch times, so you must map planned times onto a real date/time range for the same service day.

```
For times occurring after midnight on the service day, enter the time as a value greater than 24:00:00 in HH:MM:SS.
```

To compare with RT epoch:

1. determine the **service date** (e.g., from TripUpdate `start_date = 20260212`, or from your own “service day” logic)
2. determine the agency timezone (from `agency.agency_timezone`)
3. compute:

   * `planned_arrival_epoch = epoch(service_date at 00:00 in agency_tz) + seconds(arrival_time)`
   * same for departure

Then:

* `arrival_delay_sec = realtime_arrival_epoch - planned_arrival_epoch`
* `departure_delay_sec = realtime_departure_epoch - planned_departure_epoch`

### 3) Show current alerts somehow


### 4) Edge cases to keep into account:

There’s no single universal behavior — GTFS-RT feeds are produced by agency-specific systems, and in edge cases they do whatever their ops software can represent. But there are *common patterns*.

#### What can happen to a trip/vehicle during incidents

##### 1) VehiclePosition stops updating (most common)

**What you see**

* The trip/vehicle disappears from VehiclePosition entirely, or
* It keeps appearing but `timestamp` stops advancing (stale), or
* It keeps appearing with the *same coordinates* for a long time

**Why**

* GPS/device offline, radio dead zone, backend outage, vehicle swapped, etc.

**Collector rule**

* Treat VehiclePosition as **stale** if `now - vehicle.timestamp > X` (X like 120–300s depending on update frequency).

---

##### 2) TripUpdate continues but VehiclePosition disappears, or viceversa

**What you see**

* No vehicle updates, but TripUpdate still publishes stop predictions.
* The contrary

**Why**

* Predictions are generated from schedule + last known delay or control center, while GPS feed is down.
* Prediction module fails

**Collector rule**

* Keep ingesting both data sources.
* Track freshness separately for each data source.

---

##### 3) Trip is canceled: may disappear OR be explicitly marked

**Two patterns**

1. **Proper cancel:** TripUpdate appears with `trip.schedule_relationship = CANCELED` (best case)
2. **Silent cancel:** TripUpdate disappears (and maybe vehicle disappears too)

**Collector rule**

* For our case, we do not care. We store the historical data up until is not canceled, or if the trip was never made the data won't appear in the realtime.

---

##### 4) Detours / stop skipping

**What you see**

* Alerts about detour / stop closure
* TripUpdate includes stop_time_update with `schedule_relationship = SKIPPED` for some stops
* Vehicle may pass near but never STOPPED_AT

**Collector rule**

* If a stop is SKIPPED, don’t compute delay for it.
* Don’t treat “missing stop update” as “vehicle didn’t stop” automatically; it might just be the producer not sending it.

---

### The “right” mental model for your collector

### Treat each feed as a stream of snapshots

* FULL_DATASET feeds overwrite previous “current state.”
> FULL_DATASET: this feed update will overwrite all preceding realtime information for the feed. Thus this update is expected to provide a full snapshot of all known realtime information.
* Entities can vanish at any time.

So your collector should be **idempotent + stateful**:

* Store raw snapshots (bronze)
* Build a “current state” table per entity (silver)
* Emit stop-events (gold) only when you’re confident a stop has occurred or a final time is known.

---

## Practical rules to implement (so you don’t get wrecked by edge cases)

### Freshness

* `vehicle_fresh = now - vehicle.timestamp <= 180s`
* `tripupdate_fresh = now - tripupdate.timestamp <= 300s` (or based on observed cadence)

### Stop event finalization (simple, robust)

For each `(trip_instance_key, stop_id)`:

* Keep the latest predicted times from TripUpdate.
* Mark as “final” when either:

  * the stop becomes “past” (realtime time < now - grace), or
  * the vehicle has moved to a later stop (based on stop_sequence), or
  * you no longer receive updates for that stop after seeing it near-now.

Always store:

* `realtime_source = trip_update`
* `confidence = high/medium/low` (optional but helpful)

### Don’t infer from VehiclePosition unless you must

If you do inference, clearly tag it and keep it separate in analysis.

---


# Concepts I've been learning with this project 

- cosas de backend, API's, seguridad API's
- GTFS Scheduled and GTFS Realtime format and ingest ways
- Protobuf
- HTTP Polling, short polling, long polling
- WebSockets, Server-Sent Events (SSE)
