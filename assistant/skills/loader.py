"""
W18.1 Skill Loader & Format.
Handles loading of .cowork-skill packages (zipped skill definitions).
"""

import logging
import os

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger("SkillLoader")


class SkillManifest(BaseModel):
    id: str
    name: str
    version: str = "0.0.1"
    description: str
    author: str | None = "Unknown"
    rules: list[str] = Field(default_factory=list)
    system_prompts: list[str] = Field(default_factory=list, description="Content to append to system prompt")


class Skill:
    def __init__(self, manifest: SkillManifest, path: str):
        self.manifest = manifest
        self.path = path
        self.active = True


class SkillLoader:
    def __init__(self, skills_dir: str):
        self.skills_dir = skills_dir
        self.skills: dict[str, Skill] = {}

    def load_all(self):
        """Load all skills from skills directory."""
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir)

        for name in os.listdir(self.skills_dir):
            path = os.path.join(self.skills_dir, name)
            if os.path.isdir(path):
                self._load_from_dir(path)
            elif name.endswith(".cowork-skill") or name.endswith(".zip"):
                self._load_from_zip(path)

    def _load_from_dir(self, directory: str):
        yaml_path = os.path.join(directory, "skill.yaml")
        if not os.path.exists(yaml_path):
            return

        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f)

            # Load referenced prompt files
            prompts = []
            if "prompts" in data:
                # If prompts is a dict with file paths
                prompt_files = data.get("prompts", {}).get("system_files", [])
                for p_file in prompt_files:
                    p_path = os.path.join(directory, p_file)
                    if os.path.exists(p_path):
                        with open(p_path) as pf:
                            prompts.append(pf.read())

            # Add inline prompts
            if "prompts" in data and "inline" in data["prompts"]:
                prompts.extend(data["prompts"]["inline"])

            # Construct Manifest
            manifest_data = {
                "id": data.get("id"),
                "name": data.get("name"),
                "version": data.get("version", "0.0.1"),
                "description": data.get("description", ""),
                "author": data.get("author", "Unknown"),
                "rules": data.get("rules", []),
                "system_prompts": prompts,
            }

            manifest = SkillManifest(**manifest_data)
            skill = Skill(manifest, directory)
            self.skills[manifest.id] = skill
            logger.info(f"🧠 Loaded Skill: {manifest.name} ({manifest.id})")

        except Exception as e:
            logger.error(f"Failed to load skill from {directory}: {e}")

    def _load_from_zip(self, zip_path: str):
        # Extract to temp or install dir?
        # For simplicity, let's treat zip as source.
        # But we need to extract to read.
        pass  # TODO: Implement unpacking logic similar to plugins

    def get_active_system_prompts(self) -> str:
        """Combine all active skill prompts."""
        combined = []
        for skill in self.skills.values():
            if skill.active:
                if skill.manifest.rules:
                    combined.append(f"--- SKILL RULES: {skill.manifest.name} ---")
                    combined.extend([f"- {r}" for r in skill.manifest.rules])

                if skill.manifest.system_prompts:
                    combined.append(f"--- SKILL KNOWLEDGE: {skill.manifest.name} ---")
                    combined.extend(skill.manifest.system_prompts)

        return "\n".join(combined)
