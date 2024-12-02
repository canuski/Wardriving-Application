from flask import Flask, render_template
import json
import plotly.express as px
import plotly.io as pio
from collections import Counter

app = Flask(__name__)

# Helper function to load data
def load_data():
    with open('data/devices.json', 'r') as file:
        return json.load(file)

@app.route('/')
def index():
    # Load JSON data
    data = load_data()

    # Extract protocols and Wi-Fi standards
    protocols = [
        device['dot11.device']['dot11.device.advertised_ssid_map'][0]['dot11.advertisedssid.crypt_string']
        for device in data if 'dot11.device' in device
    ]
    wifi_standards = [
        device['dot11.device']['dot11.device.advertised_ssid_map'][0].get('dot11.advertisedssid.ht_mode', 'Unknown')
        for device in data if 'dot11.device' in device
    ]

    # Map ht_mode to Wi-Fi standards
    wifi_standard_map = {
        "HT20": "Wi-Fi 4",
        "HT40": "Wi-Fi 4",
        "VHT": "Wi-Fi 5",
        "HE": "Wi-Fi 6",
        "EHT": "Wi-Fi 7"
    }
    mapped_standards = [wifi_standard_map.get(standard, "Unknown") for standard in wifi_standards]

    # Count occurrences
    protocol_counts = Counter(protocols)
    wifi_standard_counts = Counter(mapped_standards)

    # Generate interactive graphs
    protocol_fig = px.pie(
        names=protocol_counts.keys(),
        values=protocol_counts.values(),
        title="Authentication Protocols"
    )
    wifi_fig = px.bar(
        x=list(wifi_standard_counts.keys()),
        y=list(wifi_standard_counts.values()),
        labels={"x": "Wi-Fi Standards", "y": "Count"},
        title="Wi-Fi Standards Distribution"
    )

    # Save graphs as HTML
    pio.write_html(protocol_fig, file="static/protocol_chart.html", auto_open=False)
    pio.write_html(wifi_fig, file="static/wifi_chart.html", auto_open=False)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)