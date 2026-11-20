"""Bend Finder – Streamlit app.

The calculation engine and dashboard are the original Bend Finder page (bend_component/index.html),
hosted as a bidirectional Streamlit component. Python handles persistence (Neon).
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import db

st.set_page_config(page_title="Bend Finder", page_icon="📐", layout="centered")
st.markdown(
    """<style>
    #MainMenu, footer, header[data-testid="stHeader"]{visibility:hidden;height:0}
    .block-container{padding:0.5rem 0.5rem 0 0.5rem;max-width:800px}
    iframe{border:0}
    </style>""",
    unsafe_allow_html=True,
)

bend_finder = components.declare_component(
    "bend_finder", path=str(Path(__file__).parent / "bend_component")
)


@st.cache_resource(show_spinner=False)
def get_store():
    return db.make_store()


store, db_error = get_store()

with st.sidebar:
    st.header("Bend Finder")
    ws = st.text_input(
        "Workspace",
        value=st.session_state.get("ws", "default"),
        help="Settings, tools and saved bends are stored under this name. Use the same name on every device.",
    ).strip() or "default"
    st.session_state["ws"] = ws
    if store.kind == "neon":
        st.success("Connected to Neon")
    else:
        st.warning(db_error or "No DATABASE_URL set – using temporary in-memory storage.")

ss = st.session_state
if ss.get("loaded_ws") != ws:
    kv = store.get_kv(ws)
    ss["store"] = {"state": kv.get("state"), "tools": kv.get("tools"), "bends": store.list_bends(ws)}
    ss["loaded_ws"] = ws
    ss["resp"] = None
    ss["last_id"] = None


def handle(req):
    """Run one request from the page; returns the response dict (or None for fire-and-forget)."""
    kind, p, rid = req["type"], req.get("payload") or {}, req["id"]
    try:
        if kind == "kv":
            store.set_kv(ws, p["key"], p["value"])
            if p["key"] in ("state", "tools"):
                ss["store"][p["key"]] = p["value"]
            return {"id": rid}
        if kind == "list_bends":
            ss["store"]["bends"] = store.list_bends(ws)
            return {"id": rid}
        if kind == "save_bend":
            rec = p["rec"]
            store.save_bend(ws, p["key"], rec["name"], int(rec["at"]), rec["state"])
            ss["store"]["bends"] = store.list_bends(ws)
            return {"id": rid}
        if kind == "delete_bend":
            store.delete_bend(ws, p["key"])
            ss["store"]["bends"] = store.list_bends(ws)
            return {"id": rid}
        return {"id": rid, "error": f"unknown request {kind}"}
    except Exception as e:  # sent back to the page and shown there
        return {"id": rid, "error": str(e)}


req = bend_finder(
    store=ss["store"],
    aiEnabled=False,
    resp=ss.get("resp"),
    key=f"bf-{ws}",
    default=None,
)

if req and req.get("id") != ss.get("last_id"):
    ss["last_id"] = req["id"]
    resp = handle(req)
    if req.get("want"):
        ss["resp"] = resp
        st.rerun()
