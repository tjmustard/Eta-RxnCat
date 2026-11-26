"""The committed JSON Schema of ``RunData`` v1.

Regenerate it with ``python3 -m eta_rxncat.review.schema``. It is
``RunData.model_json_schema()`` in pydantic's default ``validation`` mode; ``RunData`` embeds no
model with a custom serializer, so the schema is not generic anywhere.
"""

import json
from pathlib import Path

from eta_rxncat.review.run_data import SCHEMA_VERSION, RunData

SCHEMA_PATH = Path(__file__).with_name(f"run_data.v{SCHEMA_VERSION}.schema.json")
"""The committed schema file."""


def render_schema() -> str:
    """Return the text the committed schema file must hold."""
    return json.dumps(RunData.model_json_schema(), indent=2, sort_keys=True) + "\n"
