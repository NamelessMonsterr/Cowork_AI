import unittest
from assistant.agent.llm import LLMClient

class TestFallbackLogic(unittest.TestCase):
    def setUp(self):
        self.llm = LLMClient()

    def test_basic_notepad(self):
        plan = self.llm.detect_intent_fallback("Open Notepad")
        self.assertIsNotNone(plan)
        self.assertEqual(plan[0]['action'], 'launch_app')
        self.assertEqual(plan[0]['target'], 'notepad')

    def test_chrome_variations(self):
        variations = ["Launch Chrome", "Start Browser", "Open Google Chrome"]
        for v in variations:
            plan = self.llm.detect_intent_fallback(v)
            self.assertIsNotNone(plan, f"Failed to match: {v}")
            self.assertEqual(plan[0]['target'], 'chrome')

    def test_typing_chain(self):
        text = "Open Notepad and type Hello World"
        plan = self.llm.detect_intent_fallback(text)
        self.assertIsNotNone(plan)
        # Should have launch, speak, wait, type
        actions = [s['action'] for s in plan]
        self.assertIn('launch_app', actions)
        self.assertIn('type_text', actions)
        
        # Verify text content
        type_step = next(s for s in plan if s['action'] == 'type_text')
        self.assertEqual(type_step['value'], "hello world")

    def test_dangerous_commands(self):
        dangerous = [
            "please format c:", 
            "rm -rf everything", 
            "delete system32 now"
        ]
        for cmd in dangerous:
            plan = self.llm.detect_intent_fallback(cmd)
            self.assertIsNone(plan, f"Should have blocked: {cmd}")

    def test_unknown_command(self):
        plan = self.llm.detect_intent_fallback("Dance for me")
        self.assertIsNone(plan)

if __name__ == '__main__':
    unittest.main()
