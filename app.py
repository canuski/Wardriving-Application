from flask import Flask, render_template
import json
import plotly.express as px
import plotly.io as pio
import folium
from collections import Counter

app = Flask(__name__)

# Helper function to load data
def load_data():
    with open('data/devices_GPS2.json', 'r') as file:
        return json.load(file)

# Route for the main page with graphs and map
@app.route('/')
def index():
    # Load JSON data
    data = load_data()

    # Extract protocols and bandwidth modes
    protocols = []
    bandwidths = []

    for device in data:
        if 'dot11.device' in device:
            # Try to get advertised SSID data
            advertised_ssid = device['dot11.device'].get(
                'dot11.device.advertised_ssid_map', [])
            for ssid in advertised_ssid:
                crypt_string = ssid.get(
                    'dot11.advertisedssid.crypt_string', 'Unknown')
                ht_mode = ssid.get('dot11.advertisedssid.ht_mode', 'Unknown')
                protocols.append(crypt_string)
                bandwidths.append(ht_mode)

            # Try to get probed SSID data
            probed_ssid = device['dot11.device'].get(
                'dot11.device.probed_ssid_map', [])
            for ssid in probed_ssid:
                crypt_string = ssid.get(
                    'dot11.probedssid.crypt_string', 'Unknown')
                ht_mode = ssid.get('dot11.probedssid.ht_mode', 'Unknown')
                protocols.append(crypt_string)
                bandwidths.append(ht_mode)

    # Map ht_mode to bandwidth (in MHz)
    bandwidth_map = {
        "HT20": 20, "HT40": 40, "HT40-": 40, "HT40+": 40,
        "HT80": 80, "VHT": 80, "HE": 160, "EHT": 320,
    }

    # Convert the HT modes to their corresponding bandwidths
    mapped_bandwidths = [bandwidth_map.get(
        bandwidth, 'Unknown') for bandwidth in bandwidths]

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
            continue  # Skip devices without location data

    if not coordinates:
        return "No coordinates found in the data."

    # Central point for the map
    map_center = [sum(coord[1] for coord in coordinates) / len(coordinates),
                  sum(coord[0] for coord in coordinates) / len(coordinates)]

    # Create map
    mymap = folium.Map(location=map_center, zoom_start=15)

    # Add markers for each coordinate
    for coord in coordinates:
        folium.Marker(location=[coord[1], coord[0]]).add_to(mymap)

    # Save the map to an HTML file
    map_filename = 'static/map.html'
    mymap.save(map_filename)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
