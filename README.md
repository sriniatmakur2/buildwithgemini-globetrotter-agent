# GlobeTrotter — AI Travel & Experience Concierge

GlobeTrotter is a conversational travel concierge agent built with Google's Agent Development Kit (ADK) and deployed to Vertex AI Reasoning Engine with an A2UI-capable FastAPI chat frontend. It helps travelers discover personalized destinations, plan custom day-by-day itineraries, check live weather, convert currencies, look up nearby venues via Google Maps, generate AI travel postcards, and maintain long-term memory of traveler preferences across sessions.

![GlobeTrotter Demo](demo.gif)

---

## 🌟 Features & Wired Google Cloud Services

Based on the codebase in `app/` and `agents-cli-manifest.yaml`, the following services and tools are fully implemented and active:

- 🧠 **Vertex AI Memory Bank (`VertexAiMemoryBankService`)**  
  Persists user travel preferences, budget constraints, dietary restrictions, and past trip memories across sessions using ADK's `PreloadMemoryTool` and post-turn memory callbacks.

- 🗄️ **Google Cloud Firestore Catalog (`firestore_tools.py`)**  
  Queries a Firestore database for destination lookups (`search_destinations`), detailed location highlights (`get_destination_details`), and saving new travel spots (`add_destination`).

- 🎨 **Vertex AI Imagen & Cloud Storage (`image_tool.py`)**  
  Generates AI travel postcard images for destinations (`generate_travel_poster`) and uploads them to a public Google Cloud Storage bucket (`globetrotter-media-88a55e82ef51`) for inline display.

- 🗺️ **Google Maps API (`maps_tools.py`)**  
  Geocodes addresses (`geocode_address`) and retrieves nearby restaurants, hotels, cafes, and attractions (`search_nearby_places`).

- 💱 **Currency Exchange & Weather Tools (`currency_tool.py`, `weather_tool.py`)**  
  Performs real-time currency conversions (`convert_currency`) and weather condition checks (`get_live_weather`).

- 💻 **Agent Engine Code Sandbox (`AgentEngineSandboxCodeExecutor`)**  
  Executes Python code in a secure sandbox environment for complex travel budget split calculations and itinerary optimization.

- 🖼️ **A2UI Rich Surface Cards (`a2ui_utils.py`)**  
  Formats itinerary outputs and destination briefs into native A2UI interactive surface cards (Cards, Columns, Rows, Texts, Images).

- 🎨 **FastAPI Proxy Chat UI (`frontend/`)**  
  Full-featured web frontend featuring Dark/Light mode toggle, quick prompt chips, custom dialogue bubbles, and A2A protocol proxying.

### 📋 Planned / Not Yet Implemented
- Direct hotel/flight booking checkout integration.
- PDF itinerary export.

---

## 🏗️ Project Architecture

```
globetrotter-agent/
├── app/                        # Agent backend (ADK)
│   ├── agent.py                # Root agent definition & Memory Bank setup
│   ├── a2ui_utils.py           # A2UI surface callback & catalog helpers
│   ├── currency_tool.py        # Currency conversion tool
│   ├── firestore_tools.py      # Firestore destination database tools
│   ├── image_tool.py           # Vertex AI Imagen & GCS postcard generator
│   ├── maps_tools.py           # Google Maps Geocoding & Places tools
│   └── weather_tool.py         # Weather lookup tool
├── frontend/                   # Web frontend
│   ├── main.py                 # FastAPI proxy (A2A protocol)
│   └── static/
│       └── index.html          # Chat interface (Dark/Light mode, A2UI renderer)
├── agents-cli-manifest.yaml    # Agent manifest
├── demo.gif                    # Animated demo recording
└── README.md
```

---

## 🚀 Local Development Setup

### Prerequisites
- Python 3.11+
- `uv` package manager (`pip install uv`)
- Google Cloud ADK (`pip install google-adk google-genai`)
- GCP Credentials set via `gcloud auth application-default login`

### Running the Agent & Frontend Locally

1. **Install dependencies**:
   ```bash
   cd frontend
   uv sync
   ```

2. **Set environment variables**:
   ```bash
   export AGENT_DIRECTORY="app"
   export GOOGLE_MAPS_API_KEY="YOUR_API_KEY"
   ```

3. **Start the local frontend proxy**:
   ```bash
   uv run python main.py
   ```
   The application will start on port `8080`.

4. **Running local ADK Web playground** (optional):
   ```bash
   uv run adk web . --port 8080 --reload_agents
   ```
