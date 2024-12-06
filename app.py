from flask import Flask, render_template
import json
import plotly.express as px
import plotly.io as pio
from collections import Counter

app = Flask(__name__)

# Helper function to load data


def load_data():
    with open('data/devices_GPS2.json', 'r') as file:
        return json.load(file)


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
        "HT20": 20,   # HT20 corresponds to 20 MHz
        "HT40": 40,   # HT40 corresponds to 40 MHz
        "HT40-": 40,  # Negative HT40 is still 40 MHz
        "HT40+": 40,  # Positive HT40 is still 40 MHz
        "HT80": 80,   # HT80 corresponds to 80 MHz
        "VHT": 80,    # VHT is generally 80 MHz
        "HE": 160,    # HE is typically 160 MHz (Wi-Fi 6)
        "EHT": 320,   # EHT is generally 320 MHz (Wi-Fi 7)
    }

    # Convert the HT modes to their corresponding bandwidths
    mapped_bandwidths = [bandwidth_map.get(
        bandwidth, 'Unknown') for bandwidth in bandwidths]

    # Count occurrences of protocols and bandwidths
    protocol_counts = Counter(protocols)
    bandwidth_counts = Counter(mapped_bandwidths)

    print("Extracted Protocols:", protocols)
    print("Extracted Bandwidths:", bandwidths)
    print("Mapped Bandwidths:", mapped_bandwidths)

    # Generate interactive graphs
    protocol_fig = px.pie(
        names=protocol_counts.keys(),
        values=protocol_counts.values(),
        title="Authentication Protocols"
    )

    # Filter out 'Unknown' values from the bandwidth data and sort the keys
    valid_bandwidths = {k: v for k,
                        v in bandwidth_counts.items() if k != 'Unknown'}
    valid_bandwidths_sorted = dict(sorted(valid_bandwidths.items()))

    # Create a bar chart only for the available bandwidths
    bandwidth_fig = px.bar(
        x=list(valid_bandwidths_sorted.keys()),
        y=list(valid_bandwidths_sorted.values()),
        labels={"x": "Bandwidth (MHz)", "y": "Count"},
        title="Bandwidth Distribution"
    )

    # Customize the layout to properly display bandwidth categories
    bandwidth_fig.update_layout(
        xaxis=dict(
            tickmode='array',
            # Automatically set based on the available data
            tickvals=list(valid_bandwidths_sorted.keys()),
            # Dynamic labels
            ticktext=[f"{bw} MHz" for bw in valid_bandwidths_sorted.keys()],
            title="Bandwidth (MHz)",  # Title for the x-axis
        ),
        yaxis=dict(
            title="Count",  # Title for the y-axis
        ),
        showlegend=False,  # Hide the legend since we're displaying counts
    )

    # Save graphs as HTML
    pio.write_html(
        protocol_fig, file="static/protocol_chart.html", auto_open=False)
    pio.write_html(
        bandwidth_fig, file="static/bandwidth_chart.html", auto_open=False)

    return render_template('index.html')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
