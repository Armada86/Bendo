"""Neon (Postgres) storage for Bend Finder.

Two small tables, namespaced by a workspace name:
  bf_kv    – machine settings, tool library / selection, auto-pick flag
  bf_bends – named saved bends (the whole page state as JSON)

Without a DATABASE_URL the app falls back to an in-memory store (data is lost
when the server restarts) so it can still be tried out locally.
"""
import json
import os

SCHEMA = """
create table if not exists bf_kv (
    workspace  text not null,
    key        text not null,
    value      jsonb not null,
    updated_at timestamptz not null default now(),
    primary key (workspace, key)
);
create table if not exists bf_bends (
    workspace  text not null,
    key        text not null,
    name       text not null,
    at         bigint not null,
    state      jsonb not null,
    primary key (workspace, key)
);
"""


class MemoryStore:
    kind = "memory"

    def __init__(self):
        self.kv, self.bends = {}, {}

    def get_kv(self, ws):
        return dict(self.kv.get(ws, {}))

    def set_kv(self, ws, key, value):
        self.kv.setdefault(ws, {})[key] = value

    def list_bends(self, ws):
        return sorted(self.bends.get(ws, {}).values(), key=lambda r: -r["at"])

    def save_bend(self, ws, key, name, at, state):
        self.bends.setdefault(ws, {})[key] = {"key": key, "name": name, "at": at, "state": state}

    def delete_bend(self, ws, key):
        self.bends.get(ws, {}).pop(key, None)


class NeonStore:
    kind = "neon"

    def __init__(self, url):
        import psycopg
        self._psycopg = psycopg
        self.url = url
        with self._conn() as c:
            c.execute(SCHEMA)

    def _conn(self):
        # Neon scales to zero and drops idle connections, so use a short-lived one per operation.
        return self._psycopg.connect(self.url, autocommit=True, connect_timeout=15)

    def get_kv(self, ws):
        with self._conn() as c:
            rows = c.execute("select key, value from bf_kv where workspace=%s", (ws,)).fetchall()
        return {k: v for k, v in rows}

    def set_kv(self, ws, key, value):
        with self._conn() as c:
            c.execute(
                "insert into bf_kv(workspace,key,value) values (%s,%s,%s::jsonb) "
                "on conflict (workspace,key) do update set value=excluded.value, updated_at=now()",
                (ws, key, json.dumps(value)),
            )

    def list_bends(self, ws):
        with self._conn() as c:
            rows = c.execute(
                "select key,name,at,state from bf_bends where workspace=%s order by at desc", (ws,)
            ).fetchall()
        return [{"key": k, "name": n, "at": a, "state": s} for k, n, a, s in rows]

    def save_bend(self, ws, key, name, at, state):
        with self._conn() as c:
            c.execute(
                "insert into bf_bends(workspace,key,name,at,state) values (%s,%s,%s,%s,%s::jsonb) "
                "on conflict (workspace,key) do update set name=excluded.name, at=excluded.at, state=excluded.state",
                (ws, key, name, at, json.dumps(state)),
            )

    def delete_bend(self, ws, key):
        with self._conn() as c:
            c.execute("delete from bf_bends where workspace=%s and key=%s", (ws, key))


def database_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        try:
            import streamlit as st
            url = st.secrets.get("DATABASE_URL")
        except Exception:
            url = None
    return url


def make_store():
    url = database_url()
    if not url:
        return MemoryStore(), None
    try:
        return NeonStore(url), None
    except Exception as e:  # report, but keep the app usable
        return MemoryStore(), f"Could not connect to Neon: {e}"
