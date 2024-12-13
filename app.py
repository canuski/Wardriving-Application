from flask import Flask, render_template
from flask_caching import Cache
import plotly.io as pio
import plotly.express as px
import json
import os
import folium
from folium.plugins import MarkerCluster
from collections import Counter
import pandas as pd
from geopy.distance import geodesic

app = Flask(__name__)

# Configure Flask-Caching
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

# Helper function to load all JSON files from the 'cleaned_data' folder


def load_data():
    data = []
    data_folder = 'cleaned_data'  # Folder where cleaned JSON files are saved
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

# Helper function to extract protocols and bandwidths


def extract_protocols_bandwidths(data):
    protocols = []
    bandwidths = []

    for device in data:
        encryption = device.get("encryption", "Unknown")
        bandwidth = device.get("bandwidth", "Unknown")

        # Add the encryption protocol (assuming 'encryption' can have multiple values)
        protocols.append(encryption)

        # Add the bandwidth (HT40, HT80, etc.)
        bandwidths.append(bandwidth)

    # Count occurrences of protocols and bandwidths
    protocol_counts = Counter(protocols)
    bandwidth_counts = Counter(bandwidths)

    return protocol_counts, bandwidth_counts

# Route for the main page with graphs and map


@app.route('/')
@cache.cached(timeout=300)  # Cache results for 5 minutes
def index():
    # Load JSON data
    data = load_data()

    # Extract protocols and bandwidths
    protocol_counts, bandwidth_counts = extract_protocols_bandwidths(data)

    # Generate interactive graphs
    protocol_fig = px.pie(
        names=protocol_counts.keys(),
        values=protocol_counts.values(),
        title="Encryption Protocols"
    )

    valid_bandwidths = {k: v for k,
                        v in bandwidth_counts.items() if k != 'Unknown'}
    valid_bandwidths_sorted = dict(sorted(valid_bandwidths.items()))

    # Create a DataFrame for valid_bandwidths_sorted
    bandwidth_df = pd.DataFrame(valid_bandwidths_sorted.items(), columns=[
                                'Bandwidth (MHz)', 'Count'])

    # Now create the bar chart using the DataFrame
    bandwidth_fig = px.bar(
        bandwidth_df,
        x='Bandwidth (MHz)',  # Specify the column name for the x-axis
        y='Count',  # Specify the column name for the y-axis
        labels={"Bandwidth (MHz)": "Bandwidth (MHz)", "Count": "Count"},
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
        # Directly access the 'location' field, which contains [longitude, latitude]
        device["location"]
        for device in data if "location" in device
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
