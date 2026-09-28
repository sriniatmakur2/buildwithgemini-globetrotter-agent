from typing import List, Optional, Dict, Any
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-02-88a55e82ef51"
COLLECTION_NAME = "destinations"

def get_firestore_db() -> firestore.Client:
    """Returns a Firestore client initialized with the hardcoded project ID."""
    return firestore.Client(project=PROJECT_ID)

def search_destinations(
    vibe: Optional[str] = None,
    country: Optional[str] = None,
    max_daily_cost_usd: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Search travel destinations stored in the Firestore database filtered by vibe, country, or budget.

    Args:
        vibe: Optional filter by travel vibe (e.g. 'Historical & Cultural', 'Beach & Tropical Wellness', 'Adventure & Nature', 'Urban & Culinary').
        country: Optional filter by country name (e.g. 'Japan', 'France', 'Canada').
        max_daily_cost_usd: Optional upper limit for average daily cost in USD.

    Returns:
        A list of matching destination records from Firestore.
    """
    db = get_firestore_db()
    docs = db.collection(COLLECTION_NAME).stream()
    
    results = []
    for doc in docs:
        data = doc.to_dict()
        if vibe and vibe.lower() not in data.get("vibe", "").lower():
            continue
        if country and country.lower() not in data.get("country", "").lower():
            continue
        if max_daily_cost_usd and data.get("avg_daily_cost_usd", 0) > max_daily_cost_usd:
            continue
        results.append(data)
        
    return results

def get_destination_details(destination_id: str) -> Dict[str, Any]:
    """Retrieve detailed information about a specific travel destination from Firestore by its ID.

    Args:
        destination_id: The unique document ID of the destination (e.g. 'kyoto-japan', 'paris-france', 'bali-indonesia').

    Returns:
        A dictionary containing destination details, or an error message if not found.
    """
    db = get_firestore_db()
    doc_ref = db.collection(COLLECTION_NAME).document(destination_id)
    doc = doc_ref.get()
    
    if doc.exists:
        return doc.to_dict()
    else:
        return {"error": f"Destination with ID '{destination_id}' not found in Firestore."}

def add_destination(
    destination_id: str,
    name: str,
    country: str,
    vibe: str,
    budget_tier: str,
    highlights: List[str],
    avg_daily_cost_usd: int,
    description: str,
    best_season: str = "Year-round"
) -> str:
    """Add or update a travel destination in the Firestore database.

    Args:
        destination_id: Unique document ID for the destination (slug format, e.g. 'tokyo-japan').
        name: Name of the destination city or area (e.g. 'Tokyo').
        country: Country where the destination is located (e.g. 'Japan').
        vibe: Style or atmosphere (e.g. 'Futuristic & Culinary', 'Mountain Hiking').
        budget_tier: Estimated budget tier (e.g. '$', '$$', '$$$', '$$$$').
        highlights: List of key attractions or top activities.
        avg_daily_cost_usd: Estimated average daily cost per person in USD.
        description: A brief descriptive summary of the destination.
        best_season: Optimal time of year to visit.

    Returns:
        A confirmation message indicating successful creation/update in Firestore.
    """
    db = get_firestore_db()
    data = {
        "id": destination_id,
        "name": name,
        "country": country,
        "vibe": vibe,
        "budget_tier": budget_tier,
        "highlights": highlights,
        "avg_daily_cost_usd": avg_daily_cost_usd,
        "description": description,
        "best_season": best_season
    }
    
    db.collection(COLLECTION_NAME).document(destination_id).set(data)
    return f"Successfully saved destination '{name}' ({destination_id}) to Firestore collection '{COLLECTION_NAME}'."
