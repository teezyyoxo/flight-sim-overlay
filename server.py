"""
server.py - MSFS 2024 Overlay API
Version: 1.1.1
Changelog:
- Added GPS ETE (Estimated Time Enroute) in seconds.
- Added GPS ETA (Estimated Time of Arrival in Zulu time).
- Converted GPS ETA from raw seconds into HH:MM:SS format.
- Fixed SimConnect AircraftRequests() instantiation error.
"""

from flask import Flask, jsonify
from flask_cors import CORS
from SimConnect import SimConnect, AircraftRequests

app = Flask(__name__)
CORS(app)

# Connect to SimConnect
sm = SimConnect()
aq = AircraftRequests(sm) # pass SimConnect instance to AircraftRequests attribute

# SimVars to fetch
simvars = {
    "airspeed": ("AIRSPEED_INDICATED", "knots"),
    "altitude": ("PLANE_ALTITUDE", "feet"),
    "heading": ("PLANE_HEADING_DEGREES_TRUE", "degrees"),
    "latitude": ("PLANE_LATITUDE", "degrees"),
    "longitude": ("PLANE_LONGITUDE", "degrees"),
    "gps_ete": ("GPS_ETE", "seconds"),  # Estimated Time Enroute
    "gps_eta": ("GPS_ETA", "seconds"),  # Estimated Time of Arrival
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
    return jsonify({"message": "MSFS Overlay API is running. Use /data for flight data."})

@app.route("/data")
def get_flight_data():
    flight_data = {
        "airspeed": aq.get("AIRSPEED_INDICATED"),
        "altitude": aq.get("PLANE_ALTITUDE"),
        "heading": aq.get("PLANE_HEADING_DEGREES_TRUE"),
        "latitude": aq.get("PLANE_LATITUDE"),
        "longitude": aq.get("PLANE_LONGITUDE"),
        "gps_ete": aq.get("GPS_ETE"),  # Time in seconds
        "gps_eta": format_eta(aq.get("GPS_ETA")),  # Convert to readable Zulu time
    }
    return jsonify(flight_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
