# simMock: A simple Flask server that simulates a SimConnect server by providing simulated aircraft data.
#          This server is intended to be used for testing purposes only.
#          No more needing to boot up my PC just to sit at the gate in MSFS to test this lol.
#          Currently testing using the simvars that are used in my overlay. These may change over time.

from flask import Flask, jsonify
import random
import datetime

app = Flask(__name__)

VERSION = "1.1.0"
CHANGELOG = [
    "1.0.0 - Initial commit with basic SimVars.",
    "1.1.0 - Added GPS ETE and ETA simulation. Implemented versioning and changelog."
]

def generate_simvars():
    return {
        "version": VERSION,
        "airspeed": random.uniform(100, 450),     # Simulated airspeed in knots
        "altitude": random.uniform(1000, 40000),  # Simulated altitude in feet
        "heading": random.uniform(0, 360),        # Simulated heading in degrees
        "latitude": random.uniform(-90, 90),      # Simulated latitude
        "longitude": random.uniform(-180, 180),   # Simulated longitude
        "gps_ete": random.uniform(300, 3600),     # Estimated time en route in seconds
        "gps_eta": (datetime.datetime.utcnow() + datetime.timedelta(seconds=random.uniform(300, 3600))).strftime("%H:%M:%S Z")  # ETA in UTC time
    }

@app.route('/data', methods=['GET'])
def get_data():
    return jsonify(generate_simvars())

@app.route('/version', methods=['GET'])
def get_version():
    return jsonify({"version": VERSION, "changelog": CHANGELOG})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
