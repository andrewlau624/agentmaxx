import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from providers.claude import ClaudeProvider


class ContractStabilityTest(unittest.TestCase):
    """The contract is injected into every request's cached prefix.

    Non-deterministic generation or volatile content would invalidate the
    prompt cache and change billing on every install, so both are guarded
    here.
    """

    def setUp(self):
        self.provider = ClaudeProvider(source_root=REPO)

    def test_double_injection_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "CLAUDE.md"

            self.provider._inject_rules(destination)
            first = destination.read_bytes()

            self.provider._inject_rules(destination)
            second = destination.read_bytes()

        self.assertEqual(first, second)

    def test_injection_preserves_user_content_outside_markers(self):
        user_content = b"# My rules\n\nKeep my stuff.\n"
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "CLAUDE.md"
            destination.write_bytes(user_content)
            self.provider._inject_rules(destination)
            result = destination.read_bytes()

        self.assertTrue(result.startswith(user_content.rstrip(b"\n")))
        self.assertIn(b"agentmaxx:start", result)

    def test_template_contains_no_volatile_content(self):
        template = (REPO / "templates" / "CLAUDE.md").read_text()
        for token in ("{{DATE", "{{NOW", "{{TIME", "today's date"):
            self.assertNotIn(token, template)


if __name__ == "__main__":
    unittest.main()
