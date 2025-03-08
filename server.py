"""
MSFS Live Stream Overlay Server
Version: 1.0.0
Changelog:
- 1.0.0: Initial release with SimConnect data streaming (altitude, airspeed, heading).
"""

from flask import Flask, jsonify
from flask_cors import CORS
from SimConnect import SimConnect, AircraftRequests
import threading
import time

app = Flask(__name__)
CORS(app)  # Allow requests from any frontend

# Connect to SimConnect
sm = SimConnect()
aq = AircraftRequests(sm, _time=2000)  # Request updates every 2 seconds

# Flight data
flight_data = {
    "latitude": 0.0,
    "longitude": 0.0,
    "altitude": 0.0,
    "airspeed": 0.0,
    "heading": 0.0,
}

def update_data():
    """Continuously updates flight data."""
    global flight_data
    while True:
        flight_data = {
            "latitude": aq.get("PLANE_LATITUDE"),
            "longitude": aq.get("PLANE_LONGITUDE"),
            "altitude": aq.get("PLANE_ALTITUDE"),
            "airspeed": aq.get("AIRSPEED_INDICATED"),
            "heading": aq.get("PLANE_HEADING_DEGREES_MAGNETIC"),
        }
        time.sleep(1)

@app.route('/data', methods=['GET'])
def get_flight_data():
    """Returns the latest flight data."""
    return jsonify(flight_data)

@app.route('/version', methods=['GET'])
def get_version():
    """Returns the server version."""
    return jsonify({"version": "1.0.0", "changelog": "Initial release with SimConnect data streaming."})

# Start the background thread
threading.Thread(target=update_data, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
