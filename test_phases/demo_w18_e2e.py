"""
W18 Verification - E2E Skill Prompt Injection.
"""
import sys
import os
import shutil
import yaml
import asyncio
from unittest.mock import MagicMock

sys.path.append(os.getcwd())
from assistant.main import AppState, state
from assistant.skills.loader import SkillLoader
from assistant.agent.planner import Planner

APPDATA = os.path.join(os.getenv('APPDATA'), 'CoworkAI', 'skills')

def setup_appdata_skill():
    if not os.path.exists(APPDATA):
        os.makedirs(APPDATA)
    
    skill_dir = os.path.join(APPDATA, "test_skill")
    if os.path.exists(skill_dir):
        shutil.rmtree(skill_dir)
    os.makedirs(skill_dir)
    
    manifest = {
        "id": "com.cowork.test",
        "name": "Test Expert",
        "description": "Test Skill",
        "rules": ["RULE: TEST_ACTIVE"],
        "prompts": {"inline": ["PROMPT: YOU ARE A WIZARD"]}
    }
    
    with open(os.path.join(skill_dir, "skill.yaml"), 'w') as f:
        yaml.dump(manifest, f)
    
    print(f"[SETUP] Created skill at {skill_dir}")

async def test_injection():
    print("[TEST] Verifying Prompt Injection...")
    
    setup_appdata_skill()
    
    # 1. State Init
    state.skill_loader = SkillLoader(APPDATA)
    state.skill_loader.load_all()
    print(f"[STATE] Skills Loaded: {len(state.skill_loader.skills)}")
    
    # 2. Planner Init
    planner = Planner()
    
    # 3. Mock LLM Method to spy on args
    original_method = planner.llm.analyze_screen_and_plan
    planner.llm.analyze_screen_and_plan = MagicMock(return_value=None) # We don't need real return
    
    # 4. Call Create Plan
    # This invokes LLM, which we mocked.
    try:
        await planner.create_plan("Do magic")
    except:
        pass # Expected since mocked return isn't valid AgentResponse objects usually
        
    # 5. Verify Call Args
    call_args = planner.llm.analyze_screen_and_plan.call_args
    if call_args:
        kwargs = call_args.kwargs
        system_append = kwargs.get('system_append', '')
        
        print("\n--- Injected System Prompt ---")
        print(system_append)
        print("------------------------------")
        
        if "RULE: TEST_ACTIVE" in system_append and "PROMPT: YOU ARE A WIZARD" in system_append:
            print("✅ Injection SUCCESS: Rules and Prompts found.")
        else:
            print("❌ Injection FAILED: Missing content.")
    else:
        print("❌ LLM was not called.")
        
    # Cleanup
    shutil.rmtree(APPDATA)

if __name__ == "__main__":
    asyncio.run(test_injection())
