import json
import os
import glob


def clean_json(input_folder, output_folder):
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Get a list of all JSON files in the input folder
    input_files = glob.glob(os.path.join(input_folder, '*.json'))

    for input_file in input_files:
        # Load JSON data from the input file
        with open(input_file, 'r') as file:
            data = json.load(file)

        cleaned_data = []
        for device in data:
            # Extract necessary data
            cleaned_device = {
                "ssid": None,
                "encryption": None,
                "channel": None,
                "location": None,
                "bandwidth": None
            }

            dot11_device = device.get("dot11.device", {})
            advertised_ssid = dot11_device.get(
                "dot11.device.advertised_ssid_map", [])

            if advertised_ssid:
                # Assuming we only need the first SSID
                ssid_info = advertised_ssid[0]
                cleaned_device["ssid"] = ssid_info.get(
                    "dot11.advertisedssid.ssid")
                cleaned_device["encryption"] = ssid_info.get(
                    "dot11.advertisedssid.crypt_string")
                cleaned_device["channel"] = ssid_info.get(
                    "dot11.advertisedssid.channel")
                cleaned_device["location"] = ssid_info.get("dot11.advertisedssid.location", {}).get(
                    "kismet.common.location.avg_loc", {}).get("kismet.common.location.geopoint")
                cleaned_device["bandwidth"] = ssid_info.get(
                    "dot11.advertisedssid.ht_mode")

            if cleaned_device["ssid"]:  # Include only devices with a valid SSID
                cleaned_data.append(cleaned_device)

        # Generate the output filename based on the input filename
        input_filename = os.path.basename(input_file)
        output_filename = os.path.splitext(input_filename)[0] + "-cleaned.json"
        output_file = os.path.join(output_folder, output_filename)

        # Save cleaned data to the output file
        with open(output_file, 'w') as file:
            json.dump(cleaned_data, file, indent=4)

        print(f"Cleaned data saved to {output_file}")


# Specify input and output folder paths
input_folder = "data"  # Folder containing the raw JSON files
output_folder = "cleaned_data"  # Folder to save the cleaned JSON files

clean_json(input_folder, output_folder)
