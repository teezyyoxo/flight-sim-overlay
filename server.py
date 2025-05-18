from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from SimConnect import SimConnect, AircraftRequests
import os

app = Flask(__name__, static_folder="static") 

# Connect to SimConnect
sm = SimConnect()
aq = AircraftRequests(sm) 


def format_eta(seconds_since_midnight):
    
    if seconds_since_midnight is None:
        return "N/A"
    hours = int(seconds_since_midnight // 3600)
    minutes = int((seconds_since_midnight % 3600) // 60)
    seconds = int(seconds_since_midnight % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}Z"

@app.route("/")
def home():
    
    return send_from_directory("static", "index.html")

@app.route("/data")
def get_flight_data():
    
    flight_data = {
        "airspeed": aq.get("AIRSPEED_INDICATED"),
        "ground_speed": aq.get("GROUND_VELOCITY"),
        "altitude": aq.get("PLANE_ALTITUDE"),
        "heading": aq.get("PLANE_HEADING_DEGREES_MAGNETIC"),
        "latitude": aq.get("PLANE_LATITUDE"),
        "longitude": aq.get("PLANE_LONGITUDE"),
        "distance": aq.get("GPS_TARGET_DISTANCE"),
        "gps_ete": aq.get("GPS_ETE"), 
        "gps_eta": format_eta(aq.get("GPS_ETA")),  
    }
    return jsonify(flight_data)

@app.route("/<path:filename>")
def static_files(filename):
    
    return send_from_directory("static", filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
