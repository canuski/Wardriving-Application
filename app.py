from flask import Flask, render_template, url_for
from flask_caching import Cache
import plotly.express as px
import os
import json
from collections import Counter
import pandas as pd
import folium
from folium.plugins import MarkerCluster

app = Flask(__name__)

# Configure Flask-Caching
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})


# Helper function to load all JSON files from the 'cleaned_data' folder
def load_data():
    data = []
    data_folder = 'cleaned_data'
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
        filtered_protocol = [proto for proto in valid_protocols if proto in encryption.upper()]
        if filtered_protocol:
            protocols.append(filtered_protocol[0])
        else:
            protocols.append("Other")
        bandwidths.append(bandwidth)

    protocol_counts = Counter(protocols)
    bandwidth_counts = Counter(bandwidths)

    return protocol_counts, bandwidth_counts


# Helper function to extract encryption methods
def extract_encryption_methods(data):
    encryption_methods = []

    for device in data:
        encryption = device.get("encryption", "Unknown")
        if encryption != "Unknown":
            encryption_parts = encryption.split(" ")
            encryption_methods.extend([part for part in encryption_parts if part not in ["WPA2", "WPA3", "WEP", "WPA", "OPEN"]])

    encryption_counts = Counter(encryption_methods)

    return encryption_counts


# Helper function to extract and count channels
def extract_channels(data):
    channels = []

    for device in data:
        channel = device.get("channel", "Unknown")
        if channel != "Unknown":
            channels.append(channel)

    channel_counts = Counter(channels)

    return channel_counts


@app.route('/')
def index():
    data = load_data()

    # Extract data for charts
    protocol_counts, bandwidth_counts = extract_protocols_bandwidths(data)
    encryption_counts = extract_encryption_methods(data)
    channel_counts = extract_channels(data)

    # Sort channel counts for proper display
    valid_channels = {k: v for k, v in channel_counts.items() if k.isdigit()}
    sorted_channel_counts = dict(sorted(valid_channels.items(), key=lambda x: int(x[0])))

    # Summary data
    total_devices = len(data)
    most_used_protocol = max(protocol_counts, key=protocol_counts.get, default="Unknown")
    most_popular_bandwidth = max(bandwidth_counts, key=bandwidth_counts.get, default="Unknown")

    # Count SSIDs for Telenet, Proximus, Orange, Mobile Vikings, and Unknown
    telenet, proximus, orange, mobile_vikings, unknown = 0, 0, 0, 0, 0
    for device in data:
        ssid = device.get("ssid", "").lower()
        if "telenet" in ssid:
            telenet += 1
        elif "proximus" in ssid:
            proximus += 1
        elif "orange" in ssid:
            orange += 1
        elif "mobile" in ssid.lower() and "vikings" in ssid.lower():
            mobile_vikings += 1
        else:
            unknown += 1

    ssid_counts = {
        "Telenet": telenet,
        "Proximus": proximus,
        "Orange": orange,
        "Mobile Vikings": mobile_vikings,
        "Unknown": unknown
    }

    # Generate main map
    coordinates = [device for device in data if "location" in device and "ssid" in device]
    map_center = [
        sum(coord["location"][1] for coord in coordinates) / len(coordinates),
        sum(coord["location"][0] for coord in coordinates) / len(coordinates)
    ]
    mymap = folium.Map(location=map_center, zoom_start=15)
    provider_layers = {}

    # Define icons path
    icons_path = os.path.join(os.getcwd(), 'static/icons')

    for device in coordinates:
        location = device["location"]
        ssid = device.get("ssid", "Unknown SSID")
        encryption = device.get("encryption", "Unknown Encryption")
        bandwidth = device.get("bandwidth", "Unknown Bandwidth")
        channel = device.get("channel", "Unknown Channel")

        # Determine provider
        if "telenet" in ssid.lower():
            provider = "Telenet"
            icon_url = os.path.join(icons_path, "telenet.png")
        elif "proximus" in ssid.lower():
            provider = "Proximus"
            icon_url = os.path.join(icons_path, "proximus.png")
        elif "orange" in ssid.lower():
            provider = "Orange"
            icon_url = os.path.join(icons_path, "orange.png")
        elif "mobile" in ssid.lower() and "vikings" in ssid.lower():
            provider = "Mobile Vikings"
            icon_url = os.path.join(icons_path, "mobile-viking.png")
        else:
            provider = "Unknown"
            icon_url = os.path.join(icons_path, "unknown.png")

        # Add popup and markers
        popup = f"""
        <b>SSID:</b> {ssid}<br>
        <b>Encryption:</b> {encryption}<br>
        <b>Bandwidth:</b> {bandwidth}<br>
        <b>Channel:</b> {channel}
        """
        if provider not in provider_layers:
            provider_layers[provider] = folium.FeatureGroup(name=provider).add_to(mymap)

        folium.Marker(
            location=[location[1], location[0]],
            tooltip=ssid,
            popup=folium.Popup(popup, max_width=300),
            icon=folium.CustomIcon(icon_url, icon_size=(32, 32))
        ).add_to(provider_layers[provider])

    # Add provider layers and controls
    for layer in provider_layers.values():
        mymap.add_child(layer)
    folium.LayerControl().add_to(mymap)

    # Save the main map
    mymap.save('static/map.html')

    # Generate charts and save
    protocol_fig = px.pie(
        names=protocol_counts.keys(),
        values=protocol_counts.values(),
        title="Authentication Protocols"
    )
    protocol_fig.write_html('static/protocols.html')

    bandwidth_fig = px.bar(
        x=list(bandwidth_counts.keys()),
        y=list(bandwidth_counts.values()),
        title="Bandwidth Distribution",
        labels={"x": "Bandwidth (MHz)", "y": "Count"}
    )
    bandwidth_fig.write_html('static/bandwidths.html')

    encryption_fig = px.pie(
        names=encryption_counts.keys(),
        values=encryption_counts.values(),
        title="Encryption Methods"
    )
    encryption_fig.write_html('static/encryption.html')

    channel_fig = px.bar(
        x=list(sorted_channel_counts.keys()),
        y=list(sorted_channel_counts.values()),
        title="Channel Distribution",
        labels={"x": "Channel", "y": "Count"}
    )
    channel_fig.write_html('static/channels.html')

    ssid_fig = px.bar(
        x=list(ssid_counts.keys()),
        y=list(ssid_counts.values()),
        title="Provider Distribution",
        labels={"x": "Provider", "y": "Count"},
        color=list(ssid_counts.keys()),
        color_discrete_map={
            "Telenet": "#FFD700",
            "Proximus": "#6A5ACD",
            "Orange": "#FFA500",
            "Mobile Vikings": "#000000",
            "Unknown": "#808080"
        }
    )
    ssid_fig.write_html('static/ssid_distribution.html')

    # Render index template
    return render_template(
        'index.html',
        total_devices=total_devices,
        most_used_protocol=most_used_protocol,
        most_popular_bandwidth=most_popular_bandwidth,
        protocol_chart='protocols.html',
        bandwidth_chart='bandwidths.html',
        encryption_chart='encryption.html',
        channel_chart='channels.html',
        ssid_chart='ssid_distribution.html',
        map_file='map.html'
    )


@app.route('/encryption_details')
def encryption_details():
    data = load_data()

    # Extract encryption methods
    encryption_counts = extract_encryption_methods(data)

    # Detailed explanations for encryption methods
    encryption_info = {
        "AES-CCMP": "AES-CCMP is a strong encryption used in WPA2 and WPA3 networks.",
        "WPA2-PSK": "WPA2 with Pre-Shared Key (PSK) is a common security method for home networks.",
        "Open": "An open network without encryption, often used for public hotspots.",
        "WPA3-PSK": "The latest version of WPA, with improved security over WPA2.",
        "TKIP": "An outdated encryption method, often replaced by AES in modern networks.",
        "WPA2-EAP": "WPA2 with Extensible Authentication Protocol (EAP) is common for enterprise networks.",
        "WPA1": "The first version of WPA, now considered outdated and less secure.",
        "WPA1-PSK": "WPA1 with a shared key, which is less secure than modern encryption methods.",
        "WPA-PSK": "Another variant of WPA with Pre-Shared Key, often used in home networks.",
        "AES-BIP-CMAC256": "A cryptographic method that may be used for security in certain networks."
    }

    # Return the rendered template with encryption details
    return render_template(
        'encryption_details.html',
        encryption_counts=encryption_counts,
        encryption_info=encryption_info,
        encryption_chart=url_for('static', filename='encryption.html')
    )


@app.route('/bandwidth_details')
def bandwidth_details():
    data = load_data()
    
    # Extract bandwidth data
    _, bandwidth_counts = extract_protocols_bandwidths(data)
    
    # Bandwidth explanations and WiFi standards
    bandwidth_info = {
        "HT160": {
            "standard": "WiFi 6 (802.11ax) or newer",
            "description": "160 MHz channel width, offering the highest throughput. This bandwidth is only available in WiFi 6 (802.11ax) and newer standards.",
            "theoretical_speed": "Up to 9.6 Gbps (WiFi 6)",
            "use_case": "Ideal for high-density environments, gaming, and 4K/8K streaming"
        },
        "HT80": {
            "standard": "WiFi 5 (802.11ac) or newer",
            "description": "80 MHz channel width, providing high throughput. Available in WiFi 5 (802.11ac) and newer standards.",
            "theoretical_speed": "Up to 3.5 Gbps (WiFi 5)",
            "use_case": "Suitable for multiple HD streams and gaming"
        },
        "HT40": {
            "standard": "WiFi 4 (802.11n) or newer",
            "description": "40 MHz channel width. Available since WiFi 4, but also used in WiFi 5 and 6. When seen in newer networks, it might indicate a compatibility mode or congested environment.",
            "theoretical_speed": "Up to 600 Mbps (WiFi 4)",
            "use_case": "Good for general use and HD streaming"
        },
        "HT20": {
            "standard": "WiFi 4 (802.11n) or newer",
            "description": "20 MHz channel width. The base channel width available in all modern WiFi standards. When seen in newer networks, it might indicate high density environments or compatibility mode.",
            "theoretical_speed": "Up to 150 Mbps (WiFi 4)",
            "use_case": "Basic internet usage and compatibility"
        }
    }
    
    # WiFi standard summary
    wifi_standards = {
        "WiFi 6 (802.11ax)": {
            "bandwidths": ["HT20", "HT40", "HT80", "HT160"],
            "year": "2019",
            "key_features": "OFDMA, BSS Coloring, Target Wake Time"
        },
        "WiFi 5 (802.11ac)": {
            "bandwidths": ["HT20", "HT40", "HT80"],
            "year": "2014",
            "key_features": "MU-MIMO, Beamforming"
        },
        "WiFi 4 (802.11n)": {
            "bandwidths": ["HT20", "HT40"],
            "year": "2009",
            "key_features": "MIMO, Frame Aggregation"
        }
    }
    
    # Return the rendered template with bandwidth details
    return render_template(
        'bandwidth_details.html',
        bandwidth_counts=bandwidth_counts,
        bandwidth_info=bandwidth_info,
        wifi_standards=wifi_standards,
        bandwidth_chart=url_for('static', filename='bandwidths.html')
    )

@app.route('/channels_info')
def channels_info():
    # Channel information dictionary
    channel_info = {
        "2.4 GHz": {
            "channels": ["1", "6", "11"],
            "description": "Channels 1, 6, and 11 are non-overlapping and are the most suitable for use in this band.",
            "interference": "Frequently used by household devices like microwaves, which can cause interference.",
            "use_case": "Suitable for older devices and longer ranges."
        },
        "5 GHz": {
            "channels": ["36", "40", "44", "48", "149", "153", "157", "161"],
            "description": "Provides higher speeds and less interference. Channels do not overlap.",
            "interference": "Less prone to interference, ideal for modern networks.",
            "use_case": "Great for intensive applications like gaming and streaming."
        },
        "6 GHz": {
            "channels": ["1", "2", "3", "4", "..."],
            "description": "Available only for WiFi 6E devices, offering very high speeds.",
            "interference": "Minimal congestion but requires modern devices.",
            "use_case": "Perfect for future-proof networks."
        }
    }

    # Render the template for channels info
    return render_template(
        'channels_info.html',
        channel_info=channel_info
    )

@app.route('/heatmap')
def heatmap():
    data = load_data()

    # Generate heatmap data
    coordinates = [device for device in data if "location" in device and "signal-strength" in device]
    heatmap_data = [
        [device["location"][1], device["location"][0], device["signal-strength"]]
        for device in coordinates
    ]

    if not heatmap_data:
        return "No data available for heatmap generation."

    # Define map center
    map_center = [
        sum(coord[0] for coord in heatmap_data) / len(heatmap_data),
        sum(coord[1] for coord in heatmap_data) / len(heatmap_data)
    ]

    # Create a Folium map
    heatmap_map = folium.Map(location=map_center, zoom_start=15)

    # Add heatmap layer
    from folium.plugins import HeatMap
    HeatMap(heatmap_data, max_zoom=17, radius=15, blur=10).add_to(heatmap_map)

    # Save heatmap to file
    heatmap_file_path = os.path.join('static', 'heatmap.html')
    try:
        heatmap_map.save(heatmap_file_path)
    except Exception as e:
        print(f"Error saving heatmap HTML file: {e}")
        return "Error generating heatmap."


    # Render heatmap template
    return render_template('heatmap.html', heatmap_file='heatmap.html')



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
