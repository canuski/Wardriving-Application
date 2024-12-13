from flask_caching import Cache
import ijson
from collections import Counter
from folium.plugins import MarkerCluster
import folium
import plotly.io as pio
import plotly.express as px
import json
from flask import Flask, render_template
import os
from geopy.distance import geodesic
from collections import Counter


app = Flask(__name__)

# Configure Flask-Caching
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

# Helper function to load all JSON files from the 'data' folder


def load_data():
    data = []
    data_folder = 'cleaned_data'
    # Load each JSON file in the 'data' folder
    for filename in os.listdir(data_folder):
        if filename.endswith('.json'):
            file_path = os.path.join(data_folder, filename)
            with open(file_path, 'r') as file:
                try:
                    file_data = json.load(file)
                    if isinstance(file_data, list):
                        data.extend(file_data)
                    elif isinstance(file_data, dict):
                        data.append(file_data)
                except json.JSONDecodeError as e:
                    print(f"Error reading {filename}: {e}")
    return data

# Helper function to extract routes from each file


def extract_route(data):
    route = []
    previous_point = None
    for device in data:
        try:
            location = device["kismet.device.base.location"]["kismet.common.location.avg_loc"]["kismet.common.location.geopoint"]
            lat, lon = location[1], location[0]
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                current_point = (lat, lon)
                if previous_point:
                    distance = geodesic(
                        previous_point, current_point).kilometers
                    if distance > 50:  # Filter out jumps larger than 50 km
                        print(
                            f"Invalid jump from {previous_point} to {current_point} ({distance:.2f} km)")
                        continue
                route.append(current_point)
                previous_point = current_point
        except KeyError:
            continue
    return route

# Route for the main page with graphs and map


@app.route('/')
@cache.cached(timeout=300)  # Cache results for 5 minutes
def index():
    # Load JSON data
    data = load_data()

    # Extract protocols and bandwidths efficiently
    protocols = []
    bandwidths = []

    bandwidth_map = {
        "HT20": 20, "HT40": 40, "HT40-": 40, "HT40+": 40,
        "HT80": 80, "VHT": 80, "HE": 160, "EHT": 320,
    }

    for device in data:
        if 'dot11.device' not in device:
            continue
        advertised_ssid = device['dot11.device'].get(
            'dot11.device.advertised_ssid_map', [])
        probed_ssid = device['dot11.device'].get(
            'dot11.device.probed_ssid_map', [])

        for ssid in advertised_ssid + probed_ssid:
            crypt_string = ssid.get('dot11.advertisedssid.crypt_string', ssid.get(
                'dot11.probedssid.crypt_string', 'Unknown'))
            ht_mode = ssid.get('dot11.advertisedssid.ht_mode', ssid.get(
                'dot11.probedssid.ht_mode', 'Unknown'))
            protocols.append(crypt_string)
            bandwidths.append(bandwidth_map.get(ht_mode, 'Unknown'))

    # Count occurrences of protocols and bandwidths
    protocol_counts = Counter(protocols)
    bandwidth_counts = Counter(bandwidths)

    # Generate interactive graphs
    protocol_fig = px.pie(
        names=protocol_counts.keys(),
        values=protocol_counts.values(),
        title="Authentication Protocols"
    )

    valid_bandwidths = {k: v for k,
                        v in bandwidth_counts.items() if k != 'Unknown'}
    valid_bandwidths_sorted = dict(sorted(valid_bandwidths.items()))

    bandwidth_fig = px.bar(
        x=list(valid_bandwidths_sorted.keys()),
        y=list(valid_bandwidths_sorted.values()),
        labels={"x": "Bandwidth (MHz)", "y": "Count"},
        title="Bandwidth Distribution"
    )

    bandwidth_fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=list(valid_bandwidths_sorted.keys()),
            ticktext=[f"{bw} MHz" for bw in valid_bandwidths_sorted.keys()],
            title="Bandwidth (MHz)",
        ),
        yaxis=dict(title="Count"),
        showlegend=False,
    )

    # Save the charts as HTML files
    protocol_chart_filename = 'static/protocols.html'
    bandwidth_chart_filename = 'static/bandwidths.html'

    protocol_fig.write_html(protocol_chart_filename)
    bandwidth_fig.write_html(bandwidth_chart_filename)

    # Embed chart paths in the template
    protocol_chart = protocol_chart_filename
    bandwidth_chart = bandwidth_chart_filename

    # Generate the map
    coordinates = [
        (loc["kismet.common.location.avg_loc"]
         ["kismet.common.location.geopoint"])
        for device in data if "kismet.device.base.location" in device
        for loc in [device["kismet.device.base.location"]]
    ]

    if not coordinates:
        return "No coordinates found in the data."

    map_center = [
        sum(coord[1] for coord in coordinates) / len(coordinates),
        sum(coord[0] for coord in coordinates) / len(coordinates)
    ]

    mymap = folium.Map(location=map_center, zoom_start=15)
    marker_cluster = MarkerCluster().add_to(mymap)

    for coord in coordinates:
        folium.Marker(location=[coord[1], coord[0]]).add_to(marker_cluster)

    map_filename = 'static/map.html'
    mymap.save(map_filename)

    return render_template('index.html', protocol_chart=protocol_chart, bandwidth_chart=bandwidth_chart, map_file=map_filename)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
