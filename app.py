from flask import Flask, render_template, jsonify, request
from skyfield.api import load, EarthSatellite, Topos
from datetime import datetime, timedelta
import numpy as np
import folium
import logging

app = Flask(__name__)

# Load satellite TLE data
satellites = load.tle_file('http://celestrak.com/NORAD/elements/stations.txt')
by_name = {sat.name: sat for sat in satellites}

logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/satellites')
def get_satellites():
    satellite_list = list(by_name.keys())
    return jsonify({"satellites": satellite_list})

@app.route('/track')
def track_satellite():
    satellite_name = request.args.get('name', 'ISS (ZARYA)')
    satellite = by_name.get(satellite_name)

    if satellite is None:
        return jsonify({"error": "Satellite not found"}), 404

    ts = load.timescale()
    now = ts.now()
    geocentric = satellite.at(now)
    subpoint = geocentric.subpoint()

    return jsonify({
        "satellite": satellite_name,
        "latitude": subpoint.latitude.degrees,
        "longitude": subpoint.longitude.degrees,
        "altitude": subpoint.elevation.km,
        "timestamp": now.utc_strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/predict')
def predict_satellite():
    satellite_name = request.args.get('name', 'ISS (ZARYA)')
    satellite = by_name.get(satellite_name)

    if satellite is None:
        return jsonify({"error": "Satellite not found"}), 404

    ts = load.timescale()
    now = ts.now()
    times = [now + timedelta(minutes=i) for i in range(0, 180, 10)]  # Predict for 3 hours
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

@app.route('/passes')
def predict_passes():
    satellite_name = request.args.get('name', 'ISS (ZARYA)')
    latitude = float(request.args.get('lat', 0.0))
    longitude = float(request.args.get('lon', 0.0))
    altitude = float(request.args.get('alt', 0.0))
    satellite = by_name.get(satellite_name)

    if satellite is None:
        return jsonify({"error": "Satellite not found"}), 404

    ts = load.timescale()
    now = ts.now()
    t0 = ts.utc(now.utc_datetime().replace(second=0, microsecond=0))
    t1 = ts.utc(t0.utc_datetime() + timedelta(days=1))

    observer = Topos(latitude_degrees=latitude, longitude_degrees=longitude, elevation_m=altitude)
    passes = satellite.find_events(observer, t0, t1, altitude_degrees=10.0)

    pass_list = []
    for ti, event in zip(passes[0], passes[1]):
        time = ti.utc_strftime('%Y-%m-%d %H:%M:%S')
        event_name = ['rise', 'culminate', 'set'][event]
        pass_list.append({"time": time, "event": event_name})

    return jsonify({
        "satellite": satellite_name,
        "passes": pass_list
    })

@app.route('/track_map')
def track_map():
    satellite_name = request.args.get('name', 'ISS (ZARYA)')
    satellite = by_name.get(satellite_name)

    if satellite is None:
        return jsonify({"error": "Satellite not found"}), 404

    ts = load.timescale()
    now = ts.now()
    times = [now + timedelta(minutes=i) for i in range(0, 180, 10)]  # Predict for 3 hours
    latitudes = []
    longitudes = []

    for t in times:
        geocentric = satellite.at(t)
        subpoint = geocentric.subpoint()
        latitudes.append(subpoint.latitude.degrees)
        longitudes.append(subpoint.longitude.degrees)

    # Create a map centered at the first point
    m = folium.Map(location=[latitudes[0], longitudes[0]], zoom_start=2)

    # Add the ground track to the map
    for lat, lon in zip(latitudes, longitudes):
        folium.CircleMarker(location=[lat, lon], radius=2, color='blue', fill=True).add_to(m)

    # Save the map to an HTML file
    m.save('templates/map.html')

    return render_template('map.html')

@app.route('/visibility')
def check_visibility():
    satellite_name = request.args.get('name', 'ISS (ZARYA)')
    latitude = float(request.args.get('lat', 0.0))
    longitude = float(request.args.get('lon', 0.0))
    altitude = float(request.args.get('alt', 0.0))
    satellite = by_name.get(satellite_name)

    if satellite is None:
        return jsonify({"error": "Satellite not found"}), 404

    ts = load.timescale()
    now = ts.now()
    observer = Topos(latitude_degrees=latitude, longitude_degrees=longitude, elevation_m=altitude)
    difference = satellite - observer
    topocentric = difference.at(now)
    alt, az, distance = topocentric.altaz()

    return jsonify({
        "satellite": satellite_name,
        "visible": alt.degrees > 10.0,
        "altitude": alt.degrees,
        "azimuth": az.degrees,
        "distance": distance.km
    })

@app.route('/info')
def satellite_info():
    satellite_name = request.args.get('name', 'ISS (ZARYA)')
    satellite = by_name.get(satellite_name)

    if satellite is None:
        return jsonify({"error": "Satellite not found"}), 404

    return jsonify({
        "satellite": satellite_name,
        "tle_line1": satellite.model.satnum,
        "tle_line2": satellite.model.epoch.utc_strftime('%Y-%m-%d %H:%M:%S'),
        "inclination": satellite.model.inclo,
        "raan": satellite.model.nodeo,
        "eccentricity": satellite.model.ecco,
        "argument_of_perigee": satellite.model.argpo,
        "mean_anomaly": satellite.model.mo,
        "mean_motion": satellite.model.no
    })

@app.errorhandler(404)
def not_found(error):
    logging.error(f"Not found: {error}")
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)