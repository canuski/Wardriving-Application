from flask import Flask, render_template
import json
import os
import plotly.express as px
import plotly.io as pio
import folium
from collections import Counter
from geopy.distance import geodesic
import random

app = Flask(__name__)

# Helper function to load data from all files in the 'data' folder
def load_data():
    data = []
    data_folder = 'data'

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
                    print(f"Fout bij het lezen van {filename}: {e}")

    return data


# Helper function to extract the route from each file
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
                    distance = geodesic(previous_point, current_point).kilometers
                    if distance > 50: 
                        print(f"Ongeldige sprong van {previous_point} naar {current_point} ({distance:.2f} km)")
                        continue

                route.append(current_point)
                previous_point = current_point
        except KeyError:
            continue

    return route


# Route for the main page with graphs and map
@app.route('/')
def index():
    # Load JSON data from all files
    data = load_data()

    # Extract protocols and bandwidth modes
    protocols = []
    bandwidths = []

    for device in data:
        if 'dot11.device' in device:
            advertised_ssid = device['dot11.device'].get('dot11.device.advertised_ssid_map', [])
            probed_ssid = device['dot11.device'].get('dot11.device.probed_ssid_map', [])
            
            for ssid in advertised_ssid + probed_ssid:
                protocols.append(ssid.get('dot11.advertisedssid.crypt_string', 'Unknown'))
                bandwidths.append(ssid.get('dot11.advertisedssid.ht_mode', 'Unknown'))

    # Map ht_mode to bandwidth (in MHz)
    bandwidth_map = {
        "HT20": 20, "HT40": 40, "HT40-": 40, "HT40+": 40,
        "HT80": 80, "VHT": 80, "HE": 160, "EHT": 320,
    }
    mapped_bandwidths = [bandwidth_map.get(bandwidth, 'Unknown') for bandwidth in bandwidths]

    # Count occurrences of protocols and bandwidths
    protocol_counts = Counter(protocols)
    bandwidth_counts = Counter(mapped_bandwidths)

    # Generate interactive graphs
    protocol_fig = px.pie(
        names=protocol_counts.keys(),
        values=protocol_counts.values(),
        title="Authentication Protocols"
    )

    valid_bandwidths = {k: v for k, v in bandwidth_counts.items() if k != 'Unknown'}
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

    # Save graphs as HTML
    pio.write_html(protocol_fig, file="static/protocol_chart.html", auto_open=False)
    pio.write_html(bandwidth_fig, file="static/bandwidth_chart.html", auto_open=False)

    # Generate the map
    coordinates = []
    for device in data:
        try:
            location = device["kismet.device.base.location"]["kismet.common.location.avg_loc"]["kismet.common.location.geopoint"]
            coordinates.append(location)
        except KeyError:
            continue

    if not coordinates:
        return "No coordinates found in the data."

    # Central point for the map
    map_center = [sum(coord[1] for coord in coordinates) / len(coordinates),
                  sum(coord[0] for coord in coordinates) / len(coordinates)]


    # Create map
    mymap = folium.Map(location=map_center, zoom_start=15)

    # Add device markers for all coordinates from all JSON files
    for device_data in data:
        try:
            location = device_data["kismet.device.base.location"]["kismet.common.location.avg_loc"]["kismet.common.location.geopoint"]
            folium.Marker(location=[location[1], location[0]], icon=folium.Icon(color="blue")).add_to(mymap)
        except KeyError:
            continue

    # Extract and draw routes from each JSON file with different colors
    route_colors = ["blue", "green", "purple", "orange", "red", "pink", "lightblue", "darkgreen", "yellow", "darkred"]
    color_index = 0

    # Process each JSON file separately
    for filename in os.listdir('data'):
        if filename.endswith('.json'):
            file_path = os.path.join('data', filename)
            with open(file_path, 'r') as file:
                try:
                    file_data = json.load(file)
                    route_coordinates = extract_route(file_data)

                    if route_coordinates:
                        # Add polyline for this route with unique color
                        folium.PolyLine(
                            locations=route_coordinates,
                            color=route_colors[color_index % len(route_colors)],  # Use different colors for each route
                            weight=5,
                            opacity=0.8
                        ).add_to(mymap)

                        # Add markers for start and end points of the route
                        folium.Marker(route_coordinates[0], tooltip="Start", icon=folium.Icon(color="green")).add_to(mymap)
                        folium.Marker(route_coordinates[-1], tooltip="End", icon=folium.Icon(color="red")).add_to(mymap)

                except json.JSONDecodeError as e:
                    print(f"Fout bij het lezen van {filename}: {e}")
            
            color_index += 1

    # Save the map to an HTML file
    map_filename = 'static/map.html'
    mymap.save(map_filename)

    return render_template('index.html')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
