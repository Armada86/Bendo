# Bend Finder (Streamlit + Neon)

Press-brake bend planner for the MVD iBend C500-6100: material, profile, tooling and an automatic
bend sequence with collision, force, flange, throat, ram, bed and back-gauge checks.

This is the **Bend Finder** artifact moved to Streamlit with a Neon (Postgres) database.

## How it is built

| Part | Where |
|---|---|
| Calculation engine + dashboard (unchanged logic, same UI) | `bend_component/index.html`, hosted as a bidirectional Streamlit component |
| Persistence: settings, tool library/selection, saved bends | `db.py` → Neon (`bf_kv`, `bf_bends` tables, created automatically) |
| Glue (component ↔ Python requests) | `app.py` |

Differences from the artifact: browser storage / the artifact database are replaced by Neon, and the
"start from a photo of the drawing" feature is left out (it needs a paid API key outside Claude).

## Run locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # fill in DATABASE_URL
streamlit run app.py
```

Without `DATABASE_URL` the app still runs, using temporary in-memory storage.

## Neon

1. Create a project at neon.tech and copy the connection string (`postgresql://…?sslmode=require`).
2. Put it in `DATABASE_URL` (secrets file, env var, or Streamlit Community Cloud → Settings → Secrets).
3. Tables are created on first start.

## Workspace

The sidebar has a **Workspace** name. Everything saved (machine settings, added tools, saved bends) is
stored under it, so use the same name on every device to see the same data.

## Deploy

Streamlit Community Cloud: point it at this repo, main file `app.py`, add the secrets above.
