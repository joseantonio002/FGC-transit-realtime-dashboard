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