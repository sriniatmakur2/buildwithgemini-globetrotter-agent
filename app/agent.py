import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from .a2ui_utils import a2ui_callback
from .firestore_tools import search_destinations, get_destination_details, add_destination
from .weather_tool import get_live_weather
from .currency_tool import convert_currency
from .maps_tools import geocode_address, search_nearby_places
from .image_tool import generate_travel_poster


# Load Agent Engine resource name from deployment_metadata.json
deploy_metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
agent_engine_resource_name = None
memory_bank_id = "1854627626430234624"
if deploy_metadata_path.exists():
    try:
        with open(deploy_metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get("remote_agent_runtime_id")
            if agent_engine_resource_name:
                memory_bank_id = agent_engine_resource_name.split("/")[-1]
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name
)


def memory_bank_service_builder() -> VertexAiMemoryBankService:
    """Builds the Vertex AI Memory Bank service for deployment."""
    return VertexAiMemoryBankService(
        project="qwiklabs-gcp-02-88a55e82ef51",
        location="us-east1",
        agent_engine_id=memory_bank_id,
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: After each agent turn, extract and send durable facts to Memory Bank."""
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


# Build system prompt with A2uiSchemaManager (version 0.8) and BasicCatalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are GlobeTrotter, an expert AI travel concierge. "
        "You help travelers discover personalized destinations, plan itineraries, and manage travel budgets. "
        "You remember all of the user's travel plans, itineraries, booked destinations, stated preferences, dietary restrictions, and budget facts from previous conversations and use them to personalize your responses. "
        "Always check loaded past memories for existing travel plans or preferences before suggesting new options."
    ),
    workflow_description=(
        "Analyze the request and return structured UI when appropriate. "
        "Use your Firestore travel database tools (search_destinations, get_destination_details, add_destination) "
        "to search for travel options, retrieve destination details, or save new travel destinations. "
        "Use get_live_weather to check real-time weather conditions for any travel destination. "
        "Use convert_currency to convert travel budgets and costs between different currencies. "
        "Use geocode_address to convert addresses or landmarks into latitude/longitude coordinates. "
        "Use search_nearby_places to search for nearby restaurants, hotels, cafes, or attractions using coordinates. "
        "Use generate_travel_poster to generate scenic AI travel postcard images for destinations. "
        "You also have sandbox code execution capabilities to safely run Python code for complex travel calculations or data analysis."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        get_live_weather,
        convert_currency,
        geocode_address,
        search_nearby_places,
        generate_travel_poster,
        get_current_time,
        search_destinations,
        get_destination_details,
        add_destination,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
