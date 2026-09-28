"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.

Why A2A: agents-cli 1.1.0 (GA) deploys ADK agents to Agent Runtime as A2A agents
and no longer registers the reasoning-engine operation schema the old
`agent_engines.get(...).stream_query()` path relied on (operation_schemas() comes
back empty). The container serves the A2A protocol over the Agent Engine HTTP
passthrough, so this proxy fetches the agent's card and sends messages with the
a2a-sdk client (the same path `agents-cli run --mode a2a` uses). This works for
both A2A and plain ADK 1.1.0 deployments (the container serves A2A either way).

Run:
  pip install -r requirements.txt
  export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/.../reasoningEngines/..."
  export AGENT_DIRECTORY="app"   # your agent's app directory (agents-cli-manifest.yaml)
  python main.py                 # -> http://localhost:8080
"""

import os
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import json
from pathlib import Path

# Resolve AGENT_ENGINE_RESOURCE_NAME from env or deployment_metadata.json fallback
RESOURCE = os.environ.get("AGENT_ENGINE_RESOURCE_NAME", "")
if not RESOURCE:
    meta_path = Path(__file__).parent.parent / "deployment_metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                RESOURCE = json.load(f).get("remote_agent_runtime_id", "")
        except Exception:
            pass

if not RESOURCE:
    raise ValueError("AGENT_ENGINE_RESOURCE_NAME environment variable is not set and deployment_metadata.json was not found.")

# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# A2A endpoint for an Agent Runtime deployment, via the Agent Engine HTTP
# passthrough. The card lives at the well-known path under this base.
A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request (access tokens expire ~1h).
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    # Always return JSON so the browser never receives a plain-text 500 page
    # (which shows up in the chat as "Unexpected token 'I', "Internal S"... is
    # not valid JSON"). Any server-side failure now surfaces as a readable
    # message in the chat bubble instead.
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        # Agent Runtime does not serve a public card URL, so point the client at
        # the passthrough base for message sends.
        card.url = A2A_BASE
        _card = card
    return _card


import re
import json

def _normalize_a2ui_data(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    if "surfaceUpdate" in data or "beginRendering" in data:
        return data
    if "components" in data:
        return {
            "beginRendering": {
                "surfaceId": data.get("surfaceId", "default"),
                "root": data.get("root", "root"),
                "catalog": "https://a2ui.org/catalogs/basic/v0.8.json",
            },
            "surfaceUpdate": {
                "surfaceId": data.get("surfaceId", "default"),
                "components": data.get("components", []),
            },
        }
    return data


def _is_tool_debug_str(s: str) -> bool:
    if not isinstance(s, str):
        return False
    st = s.strip()
    return st.startswith("{") and ("'name':" in st or '"name":' in st) and ("'id':" in st or '"id":' in st)


def _process_text_part(text_str: str) -> list[dict]:
    """Extract embedded <a2ui-json> / <a2ui-message> tags or standalone JSON from text."""
    if not text_str or _is_tool_debug_str(text_str):
        return []

    results = []
    pattern = r'<(a2ui-[a-z]+)>(.*?)</\1>'
    matches = list(re.finditer(pattern, text_str, re.DOTALL))

    if not matches:
        trimmed = text_str.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            try:
                data = json.loads(trimmed)
                if isinstance(data, dict) and ("components" in data or "surfaceUpdate" in data or "beginRendering" in data):
                    return [{"kind": "a2ui", "data": _normalize_a2ui_data(data)}]
            except Exception:
                pass
        return [{"kind": "text", "text": text_str}]

    last_end = 0
    for match in matches:
        start, end = match.span()
        before_text = text_str[last_end:start].strip()
        if before_text:
            results.append({"kind": "text", "text": before_text})

        json_content = match.group(2).strip()
        try:
            data = json.loads(json_content)
            results.append({"kind": "a2ui", "data": _normalize_a2ui_data(data)})
        except Exception:
            results.append({"kind": "text", "text": match.group(0)})

        last_end = end

    after_text = text_str[last_end:].strip()
    if after_text:
        results.append({"kind": "text", "text": after_text})

    return results


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI."""
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            out.extend(_process_text_part(root.text))
        elif isinstance(root, str):
            out.extend(_process_text_part(root))
        elif getattr(root, "data", None) is not None:
            data = root.data
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    pass
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME or (isinstance(data, dict) and ("surfaceUpdate" in data or "beginRendering" in data or "components" in data)):
                if isinstance(data, dict):
                    data = _normalize_a2ui_data(data)
                out.append({"kind": "a2ui", "data": data})
            else:
                out.append({"kind": "text", "text": str(data)})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=message))],
            context_id=_contexts.get(user_id),
        )

        last_task = None
        got_artifact_update = False
        async for event in a2a_client.send_message(msg):
            if not isinstance(event, tuple):
                continue
            task, update = event
            if task is not None:
                last_task = task
                if getattr(task, "context_id", None):
                    _contexts[user_id] = task.context_id
            if isinstance(update, TaskArtifactUpdateEvent):
                got_artifact_update = True
                parts.extend(_extract_parts(update.artifact.parts))

        # Non-streaming fallback: pull parts from final task's artifacts or history.
        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))
            if not parts and getattr(last_task, "history", None):
                for msg_item in last_task.history:
                    role = getattr(msg_item, "role", None)
                    role_val = getattr(role, "value", str(role))
                    if role_val in ("agent", "Role.agent"):
                        meta = getattr(msg_item, "metadata", None) or {}
                        if isinstance(meta, dict) and meta.get("adk_error_code"):
                            continue
                        msg_parts = getattr(msg_item, "parts", [])
                        extracted = _extract_parts(msg_parts)
                        filtered = [
                            p for p in extracted
                            if not (p.get("kind") == "text" and ("Cannot add session to memory" in p.get("text", "") or _is_tool_debug_str(p.get("text", ""))))
                        ]
                        parts.extend(filtered)

    if not parts:
        # The turn produced no text or UI (e.g. the agent only ran tools, or a
        # tool stalled). Be honest rather than silent.
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


# Serve the chat UI (keep this mount last so /chat wins).
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
