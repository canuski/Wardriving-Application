from flask import Flask, render_template
import json
import os
import plotly.express as px
import plotly.io as pio
import folium
from folium.plugins import MarkerCluster
from collections import Counter
import ijson
from flask_caching import Cache

app = Flask(__name__)

# Configure Flask-Caching
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

# Helper function to load data lazily


def load_data():
    with open('data/1.json.json', 'r') as file:
        parser = ijson.items(file, "item")
        return [item for item in parser]

# Route for the main page with graphs and map


@app.route('/')
@cache.cached(timeout=300)  # Cache results for 5 minutes
def index():
    # Load JSON data from all files
    data = load_data()

    # Extract protocols and bandwidths efficiently
    protocols = []
    bandwidths = []

    bandwidth_map = {
        "HT20": 20, "HT40": 40, "HT40-": 40, "HT40+": 40,
        "HT80": 80, "VHT": 80, "HE": 160, "EHT": 320,
    }
    mapped_bandwidths = [bandwidth_map.get(bandwidth, 'Unknown') for bandwidth in bandwidths]

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

    # Embed charts directly into the HTML template
    protocol_chart = protocol_fig.to_html(full_html=False)
    bandwidth_chart = bandwidth_fig.to_html(full_html=False)

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
