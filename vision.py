"""Read a photographed profile drawing with Claude vision (optional – needs ANTHROPIC_API_KEY)."""
import json
import os
import re

MODEL = os.environ.get("BEND_FINDER_MODEL", "claude-sonnet-5-5")


def api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:
            key = None
    return key


def enabled():
    return bool(api_key())


def read_drawing(prompt: str, image_b64: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key())
    msg = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("The model did not return JSON.")
    return json.loads(m.group(0))
