"""Write the committed JSON Schema: ``python3 -m eta_rxncat.review.schema``."""

from eta_rxncat.review.schema import SCHEMA_PATH, render_schema

SCHEMA_PATH.write_text(render_schema(), encoding="utf-8")
print(f"wrote {SCHEMA_PATH.name}")
