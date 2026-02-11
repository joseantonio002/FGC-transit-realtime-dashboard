01/02/2026

Created a prototype just to see the components I need

03/02/2026

Lets make a log file to track how the project evolves

The objective is to build a data pipeline like the one I did in air_transport_statistics but this time making it scalable and truly autonomous by hosting it in the cloud, and making an API to the data so we can do lazy fetching instead of loading it all at once like we did in the previous project

Possible data source: [Eurostat](https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access)

Since I haven't done an API in some time, first thing I'm going to do is review some backend theory. Once I've done that, I will study what options I have to host the page the cheapest way possible. So the plan for now is:

1. Review backend theory and API's
2. Check hosting options
3. Find a data source that updates regularly and I can retrieve
4. Development

05/02/2026

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


06/02/2026

Its between [hetzner](https://www.hetzner.com/cloud/), [ionos](https://www.ionos.es/servidores/vps) and [contabo](https://contabo.com/es/vps/?utm_source=google&utm_medium=cpc&utm_campaign=brand-europe-es-eur&utm_term=generic&utm_content=contabo&gad_source=1&gad_campaignid=22529964914&gbraid=0AAAAAD_Qy-cdMpRvXJEJR0SDbQ835B9pu&gclid=CjwKCAiAv5bMBhAIEiwAqP9GuCMPRzA0dNFWWV5_LPaZbfzY6a-5XA9Iu3cRu7lk-DWj2WMO0Li5whoC7ZQQAvD_BwE).
I also have to check how to get the SSL certificate for free

10/02/2026

I will probably choose hetzner and use it for other things like trying openclaw.
So know that I know the basics, I'm going to start the develpment in my local environment for now to get this thing going and leave the cloud for later

First thing is to find some data to work with, lets explore...

11/02/2026

Thinking about either: 

- GTFS data (I have to decide schedule or realtime)
- Wheather and planes opendata

Final idea, after spending the whole afternoon checking posible data sources and thinking what I could show, I decided to use GTFS schedule data from [TITSA](https://nap.transportes.gob.es/Files/Detail/1130) and visualize routes in the map and the delay for each stop, in the last few days (using the latest GTFS data) and overall (stored data from previous days).

