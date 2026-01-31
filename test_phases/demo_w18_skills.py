"""
W18 Verification - Skill Packs.
"""

import sys
import os
import shutil
import yaml

sys.path.append(os.getcwd())
from assistant.skills.loader import SkillLoader

SKILLS_DIR = os.path.join(os.getcwd(), "test_skills_env")


def setup_mock_skill():
    if os.path.exists(SKILLS_DIR):
        shutil.rmtree(SKILLS_DIR)
    os.makedirs(SKILLS_DIR)

    skill_dir = os.path.join(SKILLS_DIR, "data_viz")
    os.makedirs(skill_dir)

    # skill.yaml
    manifest = {
        "id": "com.cowork.dataviz",
        "name": "Data Visualization Expert",
        "description": "Expert in plotting data.",
        "rules": [
            "Use matplotlib for static plots.",
            "Use seaborn for statistical plots.",
        ],
        "prompts": {
            "inline": ["When asked to plot, always check for null values first."]
        },
    }

    with open(os.path.join(skill_dir, "skill.yaml"), "w") as f:
        yaml.dump(manifest, f)


def test_skills():
    print("🧪 Testing Skill Loader...")

    setup_mock_skill()

    loader = SkillLoader(SKILLS_DIR)
    loader.load_all()

    if len(loader.skills) == 1:
        print("✅ Skill Loaded.")
        skill = loader.skills["com.cowork.dataviz"]
        print(f"  Name: {skill.manifest.name}")
        print(f"  Rules: {len(skill.manifest.rules)}")

        prompts = loader.get_active_system_prompts()
        print("\n--- Generated Prompt Context ---")
        print(prompts)
        print("-------------------------------")

        if "matplotlib" in prompts and "null values" in prompts:
            print("✅ Prompts merged correctly.")
        else:
            print("❌ Prompt merge failed.")

    else:
        print("❌ Skill Load Failed.")


if __name__ == "__main__":
    test_skills()
