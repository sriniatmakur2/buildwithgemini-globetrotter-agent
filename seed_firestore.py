import time
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-02-88a55e82ef51"
COLLECTION_NAME = "destinations"

INITIAL_DESTINATIONS = [
    {
        "id": "kyoto-japan",
        "name": "Kyoto",
        "country": "Japan",
        "vibe": "Historical & Cultural",
        "budget_tier": "$$$",
        "highlights": ["Fushimi Inari Shrine", "Arashiyama Bamboo Grove", "Gion Geisha District", "Traditional Tea Ceremony"],
        "best_season": "Spring / Autumn",
        "avg_daily_cost_usd": 160,
        "description": "Japan's cultural heart, famous for classical Buddhist temples, gardens, imperial palaces, Shinto shrines, and traditional wooden houses."
    },
    {
        "id": "paris-france",
        "name": "Paris",
        "country": "France",
        "vibe": "Urban & Culinary",
        "budget_tier": "$$$$",
        "highlights": ["Eiffel Tower", "Louvre Museum", "Montmartre", "Seine River Cruise"],
        "best_season": "Spring / Early Autumn",
        "avg_daily_cost_usd": 220,
        "description": "A global center for art, fashion, gastronomy, and culture, famed for its 19th-century cityscape crisscrossed by wide boulevards and the River Seine."
    },
    {
        "id": "bali-indonesia",
        "name": "Bali",
        "country": "Indonesia",
        "vibe": "Beach & Tropical Wellness",
        "budget_tier": "$$",
        "highlights": ["Ubud Rice Terraces", "Uluwatu Temple", "Canggu Beaches", "Mount Batur Sunrise Hike"],
        "best_season": "Dry Season (April - October)",
        "avg_daily_cost_usd": 85,
        "description": "An Indonesian island known for its forested volcanic mountains, iconic rice paddies, beaches, and coral reefs, along with vibrant Hindu culture."
    },
    {
        "id": "banff-canada",
        "name": "Banff National Park",
        "country": "Canada",
        "vibe": "Adventure & Nature",
        "budget_tier": "$$$",
        "highlights": ["Lake Louise", "Moraine Lake", "Johnston Canyon", "Icefields Parkway"],
        "best_season": "Summer (Hiking) / Winter (Skiing)",
        "avg_daily_cost_usd": 175,
        "description": "Canada's oldest national park, featuring turquoise glacial lakes, dramatic Rocky Mountain peaks, abundant wildlife, and scenic alpine trails."
    },
    {
        "id": "santorini-greece",
        "name": "Santorini",
        "country": "Greece",
        "vibe": "Romantic Coastal & Scenic",
        "budget_tier": "$$$$",
        "highlights": ["Oia Sunset Viewpoint", "Red Beach", "Akrotiri Archaeological Site", "Volcanic Winery Tours"],
        "best_season": "May to October",
        "avg_daily_cost_usd": 210,
        "description": "One of the Cyclades islands in the Aegean Sea, devastated by a volcanic eruption in the 16th century BC, shaping its rugged landscape and whitewashed cliffside towns."
    }
]

def seed_database():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    
    collection_ref = db.collection(COLLECTION_NAME)
    
    for dest in INITIAL_DESTINATIONS:
        doc_id = dest["id"]
        doc_ref = collection_ref.document(doc_id)
        
        success = False
        for attempt in range(5):
            try:
                doc_ref.set(dest)
                print(f"  ✓ Seeded destination: {dest['name']} ({doc_id})")
                success = True
                break
            except Exception as e:
                print(f"  [Attempt {attempt+1}] Retrying {doc_id} due to transient error: {e}")
                time.sleep(2)
        if not success:
            print(f"  ❌ Failed to seed {doc_id} after retries.")
        
    print(f"\nSuccessfully finished seeding script for collection '{COLLECTION_NAME}'.")

if __name__ == "__main__":
    seed_database()
