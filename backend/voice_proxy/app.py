"""
Azure Voice Live WebSocket Proxy Sub-App
=========================================
Mounts as a sub-application under the main FastAPI app.
Provides a bidirectional WebSocket proxy between browser clients
and Azure Cognitive Services Voice Agent realtime endpoint.
"""

import os
import json
import asyncio
import logging

import aiohttp
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from azure.identity import DefaultAzureCredential

from voice_proxy.voice_metadata import (
    parse_voice_live_metadata,
    extract_selected_fields,
)

logger = logging.getLogger("voice_proxy")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Configuration (env vars with defaults)
# ---------------------------------------------------------------------------
AZURE_AI_RESOURCE_NAME = os.getenv("AZURE_AI_RESOURCE_NAME", "")
AZURE_PROJECT_NAME = os.getenv("AZURE_PROJECT_NAME", "")
AZURE_EXISTING_AGENT_NAME = os.getenv("AZURE_EXISTING_AGENT_NAME", "")
AZURE_EXISTING_AGENT_VERSION = os.getenv("AZURE_EXISTING_AGENT_VERSION", "")
AZURE_EXISTING_AIPROJECT_ENDPOINT = os.getenv("AZURE_EXISTING_AIPROJECT_ENDPOINT", "")

VOICE_NAME = os.getenv("VOICE_NAME", "en-US-Ava:DragonHDLatestNeural")
VOICE_TYPE = os.getenv("VOICE_TYPE", "azure-standard")
AVATAR_CHARACTER = os.getenv("AVATAR_CHARACTER", "lisa")
AVATAR_STYLE = os.getenv("AVATAR_STYLE", "casual-sitting")
API_VERSION = os.getenv("API_VERSION", "2025-05-01-preview")

# Debug: log Azure env var status at import time (values masked)
def _mask(val: str) -> str:
    if not val:
        return "<NOT SET>"
    if len(val) <= 8:
        return f"{val[:2]}***({len(val)} chars)"
    return f"{val[:4]}...{val[-4:]}({len(val)} chars)"

logger.info("=== Voice Proxy Azure Env Vars ===")
logger.info("  AZURE_TENANT_ID       = %s", _mask(os.getenv("AZURE_TENANT_ID", "")))
logger.info("  AZURE_CLIENT_ID       = %s", _mask(os.getenv("AZURE_CLIENT_ID", "")))
logger.info("  AZURE_CLIENT_SECRET   = %s", _mask(os.getenv("AZURE_CLIENT_SECRET", "")))
logger.info("  AZURE_AI_RESOURCE_NAME= %s", _mask(AZURE_AI_RESOURCE_NAME))
logger.info("  AZURE_PROJECT_NAME    = %s", _mask(AZURE_PROJECT_NAME))
logger.info("  AGENT_NAME            = %s", _mask(AZURE_EXISTING_AGENT_NAME))
logger.info("  AGENT_VERSION         = %s", _mask(AZURE_EXISTING_AGENT_VERSION))
logger.info("  AIPROJECT_ENDPOINT    = %s", _mask(AZURE_EXISTING_AIPROJECT_ENDPOINT))
logger.info("==================================")

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
agent_metadata: dict = {}


# ---------------------------------------------------------------------------
# Sub-App
# ---------------------------------------------------------------------------
voice_app = FastAPI(title="Voice Proxy")

voice_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_token(scope: str) -> str:
    """Obtain a Bearer token via DefaultAzureCredential."""
    tenant = os.getenv("AZURE_TENANT_ID", "")
    client = os.getenv("AZURE_CLIENT_ID", "")
    secret = os.getenv("AZURE_CLIENT_SECRET", "")

    if not tenant or not client or not secret:
        missing = []
        if not tenant: missing.append("AZURE_TENANT_ID")
        if not client: missing.append("AZURE_CLIENT_ID")
        if not secret: missing.append("AZURE_CLIENT_SECRET")
        raise RuntimeError(f"Missing Azure env vars: {', '.join(missing)}")

    # Validate tenant ID format (strip whitespace, check UUID-like)
    tenant = tenant.strip()
    logger.info("Tenant ID (masked): %s", _mask(tenant))

    credential = DefaultAzureCredential()
    token = credential.get_token(scope)
    return token.token


async def _fetch_agent_metadata() -> dict:
    """Fetch Azure agent definition and parse voiceLiveConfig metadata."""
    if not AZURE_EXISTING_AIPROJECT_ENDPOINT or not AZURE_EXISTING_AGENT_NAME:
        logger.warning("Azure agent env vars not set — skipping metadata fetch.")
        return {}

    url = (
        f"{AZURE_EXISTING_AIPROJECT_ENDPOINT}/agents/"
        f"{AZURE_EXISTING_AGENT_NAME}/versions/{AZURE_EXISTING_AGENT_VERSION}"
        f"?api-version={API_VERSION}"
    )
    token = _get_token("https://ai.azure.com/")
    headers = {"Authorization": f"Bearer {token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.error("Agent fetch failed (%s): %s", resp.status, body)
                return {}
            data = await resp.json()

    metadata = data.get("metadata", {})
    flat = parse_voice_live_metadata(metadata)
    selected = extract_selected_fields(flat)
    logger.info("Agent metadata parsed: %s", selected)
    return {"raw_flat": flat, "selected": selected, "agent_id": data.get("id")}


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
@voice_app.on_event("startup")
async def on_startup():
    global agent_metadata
    try:
        agent_metadata = await _fetch_agent_metadata()
    except Exception as exc:
        logger.exception("Failed to fetch agent metadata on startup: %s", exc)
        agent_metadata = {}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@voice_app.get("/")
async def health():
    return {"status": "ok", "service": "voice-proxy"}


@voice_app.get("/config")
async def config():
    return agent_metadata


# ---------------------------------------------------------------------------
# WebSocket proxy
# ---------------------------------------------------------------------------
@voice_app.websocket("/ws")
async def ws_proxy(
    websocket: WebSocket,
    agentName: str | None = None,
    projectName: str | None = None,
    voice: str | None = None,
):
    await websocket.accept()

    agent_name = agentName or AZURE_EXISTING_AGENT_NAME
    project_name = projectName or AZURE_PROJECT_NAME
    voice_name = voice or VOICE_NAME

    azure_ws_url = (
        f"wss://{AZURE_AI_RESOURCE_NAME}.cognitiveservices.azure.com/"
        f"voice-agent/realtime"
        f"?api-version={API_VERSION}"
        f"&agent-name={agent_name}"
        f"&agent-project-name={project_name}"
    )

    token = _get_token("https://ai.azure.com/.default")
    extra_headers = {"Authorization": f"Bearer {token}"}

    try:
        async with websockets.connect(
            azure_ws_url,
            additional_headers=extra_headers,
        ) as azure_ws:
            # Send initial session.update
            session_update = {
                "type": "session.update",
                "session": {
                    "avatar": {
                        "character": AVATAR_CHARACTER,
                        "style": AVATAR_STYLE,
                    },
                    "voice": {
                        "name": voice_name,
                        "type": VOICE_TYPE,
                    },
                    "input_audio_noise_reduction": {"type": "near_field"},
                    "input_audio_echo_cancellation": {"type": "server_echo_cancellation"},
                    "turn_detection": {"type": "server_vad"},
                },
            }
            await azure_ws.send(json.dumps(session_update))
            logger.info("Sent session.update to Azure")

            # Bidirectional forwarding
            await _bridge(websocket, azure_ws)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as exc:
        logger.exception("WebSocket proxy error: %s", exc)
        try:
            await websocket.close(code=1011, reason=str(exc)[:120])
        except Exception:
            pass


async def _bridge(client_ws: WebSocket, azure_ws):
    """Forward messages bidirectionally until one side closes."""

    async def client_to_azure():
        try:
            while True:
                data = await client_ws.receive_text()
                await azure_ws.send(data)
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    async def azure_to_client():
        try:
            async for message in azure_ws:
                if isinstance(message, str):
                    await client_ws.send_text(message)
                else:
                    await client_ws.send_bytes(message)
        except Exception:
            pass

    # Run both directions; when one finishes the other is cancelled
    done, pending = await asyncio.wait(
        [
            asyncio.ensure_future(client_to_azure()),
            asyncio.ensure_future(azure_to_client()),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
