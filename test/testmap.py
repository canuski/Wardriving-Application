import json
import folium

# JSON-bestand inlezen
with open('devices_GPS2.json', 'r') as file:
    data = json.load(file)

# Coördinaten verzamelen
coordinates = []
for device in data:
    try:
        location = device["kismet.device.base.location"]["kismet.common.location.avg_loc"]["kismet.common.location.geopoint"]
        coordinates.append(location)
    except KeyError:
        continue  # Sla apparaten over zonder locatiegegevens

# Controleer of er coördinaten zijn
if not coordinates:
    print("Geen coördinaten gevonden in het bestand.")
    exit()

# Centraal punt voor de kaart bepalen
map_center = [sum(coord[1] for coord in coordinates) / len(coordinates),
              sum(coord[0] for coord in coordinates) / len(coordinates)]

# Kaart maken
mymap = folium.Map(location=map_center, zoom_start=15)

# Punten toevoegen aan de kaart
for coord in coordinates:
    folium.Marker(location=[coord[1], coord[0]]).add_to(mymap)

# Kaart opslaan
mymap.save("map.html")
print("De kaart is opgeslagen als map.html.")
