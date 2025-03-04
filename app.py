from flask import Flask, render_template, jsonify
from skyfield.api import load, EarthSatellite
from datetime import datetime, timedelta
import numpy as np

app = Flask(__name__)

# Load satellite TLE data
satellites = load.tle_file('http://celestrak.com/NORAD/elements/stations.txt')
by_name = {sat.name: sat for sat in satellites}

@app.route('/')
def index():
    return render_template('index.html', satellite="ISS (ZARYA)")

@app.route('/track')
def track_satellite():
    satellite_name = "ISS (ZARYA)"
    satellite = by_name.get(satellite_name)

    if satellite is None:
        return jsonify({"error": "Satellite not found"}), 404

    ts = load.timescale()
    now = ts.now()
    times = [now + timedelta(minutes=i) for i in range(30)]  # Simulate 30 minutes of data
    latitudes = []
    longitudes = []

    for t in times:
        geocentric = satellite.at(t)
        subpoint = geocentric.subpoint()
        latitudes.append(subpoint.latitude.degrees)
        longitudes.append(subpoint.longitude.degrees)

    return jsonify({
        "satellite": satellite_name,
        "latitudes": latitudes,
        "longitudes": longitudes,
        "timestamps": [t.utc_strftime('%Y-%m-%d %H:%M:%S') for t in times]
    })

if __name__ == '__main__':
    app.run(debug=True)