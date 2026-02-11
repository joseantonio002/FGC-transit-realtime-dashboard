# Sales Dashboard Prototype - Local API + Static Frontend

## Project Goal
Create a prototype demonstrating:
- A local API that serves data from a CSV file
- A static HTML page with Plotly visualization
- Lazy fetching: the frontend calls the API to get data
- Interactive filtering by store

## Project Structure
```
scalable-data-pipeline/
├── backend/
│   ├── data/
│   │   └── sales.csv
│   ├── api.py
│   └── requirements.txt
└── docs/
    └── index.html
```

## Step 1: Create Sample Data

Create `backend/data/sales.csv` with the following content:
```csv
Quarter,Store,Sales
Q1 2024,Store A,45000
Q1 2024,Store B,52000
Q1 2024,Store C,38000
Q2 2024,Store A,48000
Q2 2024,Store B,55000
Q2 2024,Store C,41000
Q3 2024,Store A,51000
Q3 2024,Store B,58000
Q3 2024,Store C,44000
Q4 2024,Store A,62000
Q4 2024,Store B,68000
Q4 2024,Store C,53000
```

## Step 2: Create Backend API

Create `backend/api.py` - a simple Flask API that:
- Reads the CSV file
- Provides an endpoint to get all stores (for the filter dropdown)
- Provides an endpoint to get sales data filtered by store
- Enables CORS so the frontend can call it from a different origin

Requirements:
- Use Flask for the web server
- Use pandas to read and filter the CSV
- Use flask-cors to enable CORS
- Create these endpoints:
  - `GET /api/stores` - returns list of unique stores
  - `GET /api/sales?store=<store_name>` - returns sales data for a specific store
  - Both endpoints should return JSON

Create `backend/requirements.txt`:
```
flask
pandas
flask-cors
```

## Step 3: Create Frontend

Create `docs/index.html` - a static HTML page that:
- Has a dropdown/select to choose a store
- Fetches the list of stores from the API on page load
- When a store is selected, fetches that store's sales data from the API
- Displays the data as a Plotly bar chart (Quarter on x-axis, Sales on y-axis)
- Shows a loading indicator while fetching data
- Handles errors gracefully

Requirements:
- Use vanilla JavaScript (no frameworks needed for this prototype)
- Use Plotly.js from CDN for visualization
- Make it visually clean and simple
- The API URL should be configurable (default: `http://localhost:5000`)

## Step 4: Instructions for Running

Include clear instructions in comments or at the top of files for:

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python api.py
# Should run on http://localhost:5000
```

**Frontend:**
```bash
cd docs
# Option 1: Use Python's built-in server
python -m http.server 8000
# Then open http://localhost:8000

# Option 2: Just open index.html directly in browser
# (may have CORS issues depending on browser)
```

## Step 5: Testing the Prototype

After running both:
1. Backend should be at http://localhost:5000
2. Frontend should be at http://localhost:8000 (or opened directly)
3. Open browser console to see API calls being made
4. Select different stores and see the chart update with fresh data from API

## Success Criteria

- ✅ Backend API serves data from CSV
- ✅ Frontend fetches stores list on load
- ✅ Changing store selection triggers new API call
- ✅ Chart updates with new data (lazy fetching)
- ✅ No hardcoded data in the frontend
- ✅ Clean separation: data lives in backend, frontend just displays

## Notes for Future GitHub Pages Deployment

Currently this runs locally. To deploy to GitHub Pages:
1. The `docs/index.html` can be hosted on GitHub Pages as-is
2. The backend API would need to be deployed to Vercel/Render/etc.
3. Update the API URL in the frontend to point to the deployed backend
4. That's it! Static frontend + separate API backend

## What to Create

Please create all the files described above with:
- Clean, well-commented code
- Error handling
- Simple but professional styling
- Console logs to show what's happening (for learning)
