"""
Macro Storage - Persist learned workflows (W8.3).

Structure:
- .conversations/macros/{id}/
    - plan.json (ExecutionPlan)
    - metadata.json (Version, Author, Stats)
    - preview.png (Optional)
"""

import json
import logging
import os
import uuid
from datetime import datetime

from assistant.ui_contracts.schemas import ExecutionPlan

logger = logging.getLogger("MacroStorage")

MACRO_DIR = os.path.join(os.getcwd(), ".conversations", "macros")


class MacroStorage:
    def __init__(self):
        os.makedirs(MACRO_DIR, exist_ok=True)

    def save_macro(self, plan: ExecutionPlan, metadata: dict) -> str:
        """Save a new macro."""
        macro_id = plan.id or str(uuid.uuid4())
        folder = os.path.join(MACRO_DIR, macro_id)
        os.makedirs(folder, exist_ok=True)

        # 1. Save Plan
        with open(os.path.join(folder, "plan.json"), "w") as f:
            try:
                # Pydantic V2
                f.write(plan.model_dump_json(indent=2))
            except AttributeError:
                # Pydantic V1 fallback
                f.write(plan.json(indent=2))

        # 2. Save Metadata
        metadata["id"] = macro_id
        metadata["saved_at"] = datetime.now().isoformat()
        metadata["macro_version"] = 1

        with open(os.path.join(folder, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved macro {macro_id} to {folder}")
        return macro_id

    def list_macros(self) -> list[dict]:
        """List all saved macros."""
        macros = []
        if not os.path.exists(MACRO_DIR):
            return []

        for name in os.listdir(MACRO_DIR):
            meta_path = os.path.join(MACRO_DIR, name, "metadata.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                        macros.append(meta)
                except Exception:
                    continue
        return sorted(macros, key=lambda x: x.get("saved_at", ""), reverse=True)

    def load_plan(self, macro_id: str) -> ExecutionPlan | None:
        """Load execution plan for a macro."""
        path = os.path.join(MACRO_DIR, macro_id, "plan.json")
        if not os.path.exists(path):
            return None

        try:
            with open(path) as f:
                data = json.load(f)
                return ExecutionPlan(**data)
        except Exception as e:
            logger.error(f"Failed to load macro {macro_id}: {e}")
            return None
