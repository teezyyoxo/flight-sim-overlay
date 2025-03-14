"""
server.py - MSFS 2024 Overlay API
Version: 1.4.0
Changelog:
- Added GPS DESTINATION DISTANCE to the flight data API.
- Added ETA calculation.
- Added source and destination airport ICAO codes.
- Updated /data route to include new fields.
- Preserved all existing functionality and comments.
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from SimConnect import SimConnect, AircraftRequests
import os

app = Flask(__name__, static_folder="static")  # Set static folder for serving files
CORS(app)

# Connect to SimConnect
sm = SimConnect()
aq = AircraftRequests(sm)  # Pass SimConnect instance to AircraftRequests attribute

# SimVars to fetch
simvars = {
    "airspeed": ("AIRSPEED_INDICATED", "knots"),
    "altitude": ("PLANE_ALTITUDE", "feet"),
    "heading": ("PLANE_HEADING_DEGREES_TRUE", "degrees"),
    "latitude": ("PLANE_LATITUDE", "degrees"),
    "longitude": ("PLANE_LONGITUDE", "degrees"),
    "gps_ete": ("GPS_ETE", "seconds"),  # Estimated Time Enroute
    "gps_eta": ("GPS_ETA", "seconds"),  # Estimated Time of Arrival
    "distance_remaining": ("GPS DESTINATION DISTANCE", "nautical miles"),  # Distance to destination
    "departure_icao": ("GPS ORIGIN AIRPORT", "string"),  # Departure airport ICAO
    "destination_icao": ("GPS DESTINATION AIRPORT", "string"),  # Destination airport ICAO
}

def format_eta(seconds_since_midnight):
    """Converts seconds since midnight to HH:MM:SSZ format."""
    if seconds_since_midnight is None:
        return "N/A"
    hours = int(seconds_since_midnight // 3600)
    minutes = int((seconds_since_midnight % 3600) // 60)
    seconds = int(seconds_since_midnight % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}Z"

@app.route("/")
def home():
    """Serve the main overlay HTML page."""
    return send_from_directory("static", "index.html")

@app.route("/data")
def get_flight_data():
    """Fetch and return flight simulation data in JSON format."""
    flight_data = {
        "airspeed": aq.get("AIRSPEED_INDICATED"),
        "altitude": aq.get("PLANE_ALTITUDE"),
        "heading": aq.get("PLANE_HEADING_DEGREES_TRUE"),
        "latitude": aq.get("PLANE_LATITUDE"),
        "longitude": aq.get("PLANE_LONGITUDE"),
        "gps_ete": aq.get("GPS_ETE"),  # Time in seconds
        "gps_eta": format_eta(aq.get("GPS_ETA")),  # Convert to readable Zulu time
        "distance_remaining": aq.get("GPS DESTINATION DISTANCE"),  # Distance in nautical miles
        "departure_icao": aq.get("GPS ORIGIN AIRPORT"),  # Departure ICAO
        "destination_icao": aq.get("GPS DESTINATION AIRPORT"),  # Destination ICAO
    }
    return jsonify(flight_data)

@app.route("/<path:filename>")
def static_files(filename):
    """Serve other static files such as CSS, JS, and images."""
    return send_from_directory("static", filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
