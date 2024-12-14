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
import json_fix

app = Flask(__name__)

# Configure Flask-Caching
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

# Helper function to load all JSON files from the 'cleaned_data' folder
def load_data():
    json_fix.clean_json('data', 'cleaned_data')
    data = []
    data_folder = 'cleaned_data'  # Folder where cleaned JSON files are saved
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

# Helper function to filter encryption protocols and extract bandwidths
def extract_protocols_bandwidths(data):
    valid_protocols = ["WPA2", "WPA3", "WEP", "WPA", "OPEN"]
    protocols = []
    bandwidths = []

    for device in data:
        encryption = device.get("encryption", "Unknown")
        bandwidth = device.get("bandwidth", "Unknown")

        # Filter encryption protocols to include only valid protocols
        filtered_protocol = [proto for proto in valid_protocols if proto in encryption.upper()]
        if filtered_protocol:
            protocols.append(filtered_protocol[0])  # Take the first matching protocol
        else:
            protocols.append("Other")

        # Add the bandwidth (HT40, HT80, etc.)
        bandwidths.append(bandwidth)

    # Count occurrences of protocols and bandwidths
    protocol_counts = Counter(protocols)
    bandwidth_counts = Counter(bandwidths)

    return protocol_counts, bandwidth_counts

# Helper function to extract encryption methods
def extract_encryption_methods(data):
    encryption_methods = []

    for device in data:
        encryption = device.get("encryption", "Unknown")
        if encryption != "Unknown":
            # Extract the encryption methods from the string
            encryption_parts = encryption.split(" ")
            encryption_methods.extend([part for part in encryption_parts if part not in ["WPA2", "WPA3", "WEP", "WPA", "OPEN"]])

    # Count occurrences of encryption methods
    encryption_counts = Counter(encryption_methods)

    return encryption_counts

# Helper function to extract and count channels
def extract_channels(data):
    channels = []

    for device in data:
        channel = device.get("channel", "Unknown")
        if channel != "Unknown":
            channels.append(channel)

    # Count occurrences of channels
    channel_counts = Counter(channels)

    return channel_counts

# Route for the main page with graphs and map
@app.route('/')
@cache.cached(timeout=300)  # Cache results for 5 minutes
def index():
    # Load JSON data
    data = load_data()

    # Extract protocols and bandwidths
    protocol_counts, bandwidth_counts = extract_protocols_bandwidths(data)

    # Extract encryption methods
    encryption_counts = extract_encryption_methods(data)
    
    # Extract channels
    channel_counts = extract_channels(data)

    # Generate interactive graphs
    protocol_fig = px.pie(
        names=protocol_counts.keys(),
        values=protocol_counts.values(),
        title="Authentication Protocols"
    )

    valid_bandwidths = {k: v for k, v in bandwidth_counts.items() if k != 'Unknown'}
    valid_bandwidths_sorted = dict(sorted(valid_bandwidths.items()))

    # Create a DataFrame for valid_bandwidths_sorted
    bandwidth_df = pd.DataFrame(valid_bandwidths_sorted.items(), columns=[
        'Bandwidth (MHz)', 'Count'])

    # Now create the bar chart using the DataFrame
    bandwidth_fig = px.bar(
        bandwidth_df,
        x='Bandwidth (MHz)',
        y='Count',
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

    encryption_fig = px.pie(
        names=encryption_counts.keys(),
        values=encryption_counts.values(),
        title="Encryption Methods"
    )
    
    # Generate the channel bar chart
    channel_fig = px.bar(
        x=list(channel_counts.keys()),
        y=list(channel_counts.values()),
        labels={"x": "Channel", "y": "Count"},
        title="Channel Distribution"
    )

    # Save the charts as HTML files
    protocol_chart_filename = 'static/protocols.html'
    bandwidth_chart_filename = 'static/bandwidths.html'
    encryption_chart_filename = 'static/encryption.html'
    channel_chart_filename = 'static/channels.html'

    protocol_fig.write_html(protocol_chart_filename)
    bandwidth_fig.write_html(bandwidth_chart_filename)
    encryption_fig.write_html(encryption_chart_filename)
    channel_fig.write_html(channel_chart_filename)
    
    # Embed chart paths in the template
    protocol_chart = protocol_chart_filename
    bandwidth_chart = bandwidth_chart_filename
    encryption_chart = encryption_chart_filename
    channel_chart = channel_chart_filename
    
    # Generate the map with SSID on hover
    coordinates = [
        device for device in data if "location" in device and "ssid" in device
    ]

    if not coordinates:
        return "No coordinates found in the data."

    map_center = [
        sum(coord["location"][1] for coord in coordinates) / len(coordinates),
        sum(coord["location"][0] for coord in coordinates) / len(coordinates)
    ]

    mymap = folium.Map(location=map_center, zoom_start=15)
    marker_cluster = MarkerCluster().add_to(mymap)

    for device in coordinates:
        location = device["location"]
        ssid = device.get("ssid", "Unknown SSID")  # Get SSID, or default to 'Unknown SSID'
        
        # Create a tooltip to show SSID on hover
        tooltip = folium.Tooltip(ssid)
        folium.Marker(
            location=[location[1], location[0]],  # Latitude, Longitude
            tooltip=tooltip
        ).add_to(marker_cluster)

    # Save map to file
    map_filename = 'static/map.html'
    mymap.save(map_filename)

    return render_template('index.html', protocol_chart=protocol_chart, bandwidth_chart=bandwidth_chart, encryption_chart=encryption_chart, channel_chart=channel_chart, map_file=map_filename)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
