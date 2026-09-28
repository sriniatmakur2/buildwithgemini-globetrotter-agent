import os
import json
import urllib.request
import urllib.parse
from typing import Dict, List, Any

def get_maps_api_key() -> str:
    """Retrieve Google Maps API key from environment variables."""
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable is not set.")
    return api_key

def geocode_address(address: str) -> Dict[str, Any]:
    """Convert an address or location name into geographic coordinates (latitude and longitude) using Google Geocoding API.

    Args:
        address: The address or place name to geocode (e.g., 'Kyoto Station, Japan', 'Eiffel Tower, Paris').

    Returns:
        A dictionary containing the name, formatted address, and location coordinates (latitude and longitude).
    """
    try:
        api_key = get_maps_api_key()
        encoded_address = urllib.parse.quote(address)
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
        
        req = urllib.request.Request(url, headers={"User-Agent": "GlobeTrotterAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
        if data.get("status") != "OK" or not data.get("results"):
            return {"error": f"Unable to geocode address '{address}'. Status: {data.get('status')}"}
            
        result = data["results"][0]
        formatted_address = result.get("formatted_address", address)
        location = result["geometry"]["location"]
        
        return {
            "name": address,
            "address": formatted_address,
            "location": {
                "latitude": location["lat"],
                "longitude": location["lng"]
            }
        }
    except Exception as e:
        return {"error": f"Geocoding error: {str(e)}"}

def search_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "restaurant",
    radius_meters: float = 1000.0,
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """Find nearby places of a specific type (e.g. restaurant, tourist_attraction, cafe, lodging) using Google Places API (New).

    Args:
        latitude: Latitude of the center search coordinate.
        longitude: Longitude of the center search coordinate.
        place_type: Type of place to search for (e.g., 'restaurant', 'tourist_attraction', 'cafe', 'lodging', 'museum'). Default is 'restaurant'.
        radius_meters: Search radius in meters (default is 1000.0).
        max_results: Maximum number of place results to return (default is 5).

    Returns:
        A list of place dictionaries containing key fields (name, address, location).
    """
    try:
        api_key = get_maps_api_key()
        places_url = "https://places.googleapis.com/v1/places:searchNearby"
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
        }
        
        payload = {
            "includedTypes": [place_type],
            "maxResultCount": min(max_results, 10),
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "radius": float(radius_meters)
                }
            }
        }
        
        body_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(places_url, data=body_bytes, headers=headers, method="POST")
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
        places_list = data.get("places", [])
        results = []
        for place in places_list:
            display_name = place.get("displayName", {}).get("text", "Unknown Place")
            formatted_address = place.get("formattedAddress", "N/A")
            loc = place.get("location", {})
            
            results.append({
                "name": display_name,
                "address": formatted_address,
                "location": {
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude")
                }
            })
            
        return results
    except Exception as e:
        return [{"error": f"Error searching nearby places: {str(e)}"}]
