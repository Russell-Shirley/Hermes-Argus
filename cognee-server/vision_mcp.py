"""MCP stdio server exposing vision__describe_image via local Ollama moondream.

The vision model loads JIT on first call and stays warm for VISION_KEEP_ALIVE
(default: "5m") before self-evicting from VRAM.

Pull the model first: ollama pull moondream
"""
import base64
import json
import logging
import os

import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
VISION_MODEL = os.environ.get("VISION_MODEL", "moondream")
VISION_KEEP_ALIVE = os.environ.get("VISION_KEEP_ALIVE", "5m")

_DEFAULT_PROMPT = (
    "Describe this image in detail, including all visible text, UI elements, "
    "data, charts, and key information. Be specific and thorough."
)

mcp = FastMCP("argus-vision")


@mcp.tool(
    name="vision__describe_image",
    description=(
        "Fetch an image from a URL, send it to the local Ollama vision model (moondream), "
        "and return a detailed text description. Use when the user sends an image or "
        "screenshot that should be analyzed or stored in memory."
    ),
)
async def describe_image(url: str, prompt: str = _DEFAULT_PROMPT) -> str:
    """Download image from url, base64-encode it, and run through the vision model."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            img_resp = await client.get(url)
            img_resp.raise_for_status()
            b64 = base64.b64encode(img_resp.content).decode()

        payload = {
            "model": VISION_MODEL,
            "prompt": prompt,
            "images": [b64],
            "keep_alive": VISION_KEEP_ALIVE,
            "stream": False,
        }

        # Separate client with longer timeout for model inference
        async with httpx.AsyncClient(timeout=120.0) as client:
            vision_resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
            )
            vision_resp.raise_for_status()

        data = vision_resp.json()
        description = data.get("response", "").strip()
        return description or "[Vision model returned an empty response]"

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        logger.warning("vision__describe_image HTTP %d: %s", status, e)
        return f"[Image could not be described — HTTP {status} from vision model]"
    except httpx.RequestError as e:
        logger.warning("vision__describe_image connection error: %s", e)
        return f"[Image could not be described — vision model unavailable ({type(e).__name__})]"
    except Exception as e:
        logger.error("vision__describe_image unexpected error: %s", e, exc_info=True)
        return f"[Image could not be described — {type(e).__name__}]"


if __name__ == "__main__":
    mcp.run(transport="stdio")
