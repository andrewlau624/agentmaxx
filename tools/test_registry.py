"""Consistency checks across tools, the registry, and the contract template.

The registry listed 4 of 10 tools and two READMEs still referenced
pre-rename paths. These assertions make that class of drift a test
failure rather than something an agent discovers at runtime.
"""

import re
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_ROOT.parent
REGISTRY = TOOLS_ROOT / "registry.yaml"
TEMPLATE = REPO_ROOT / "templates" / "CLAUDE.md"


def tool_directories() -> set[str]:
    return {
        path.name
        for path in TOOLS_ROOT.iterdir()
        if path.is_dir() and path.name.startswith("better-")
    }


def registry_entries() -> dict[str, str]:
    """Map tool name to script path, parsed without a YAML dependency."""
    entries: dict[str, str] = {}
    name = None

    for line in REGISTRY.read_text().splitlines():
        name_match = re.match(r"\s*-\s+name:\s*(\S+)", line)
        script_match = re.match(r"\s*script:\s*(\S+)", line)

        if name_match:
            name = name_match.group(1)
        elif script_match and name:
            entries[name] = script_match.group(1)

    return entries


class TestRegistryConsistency(unittest.TestCase):
    def test_every_tool_has_a_registry_entry(self):
        self.assertEqual(tool_directories(), set(registry_entries()))

    def test_every_registry_script_exists(self):
        for name, script in registry_entries().items():
            with self.subTest(tool=name):
                self.assertTrue((TOOLS_ROOT / script).is_file(), script)

    def test_every_tool_has_a_readme(self):
        for name in tool_directories():
            with self.subTest(tool=name):
                self.assertTrue((TOOLS_ROOT / name / "README.md").is_file())

    def test_every_tool_has_tests(self):
        for name in tool_directories():
            with self.subTest(tool=name):
                module = name.replace("-", "_")
                self.assertTrue(
                    (TOOLS_ROOT / name / f"test_{module}.py").is_file()
                )

    def test_readmes_reference_real_script_paths(self):
        pattern = re.compile(r"python3 (tools/\S+\.py)")

        for name in tool_directories():
            readme = TOOLS_ROOT / name / "README.md"

            for referenced in pattern.findall(readme.read_text()):
                with self.subTest(tool=name, path=referenced):
                    self.assertTrue(
                        (REPO_ROOT / referenced).is_file(),
                        f"{name}/README.md references missing {referenced}",
                    )


class TestTemplateConsistency(unittest.TestCase):
    def test_template_documents_every_tool(self):
        template = TEMPLATE.read_text()

        for name in tool_directories():
            with self.subTest(tool=name):
                self.assertIn(name, template)

    def test_template_uses_the_tools_root_placeholder(self):
        self.assertIn("{{TOOLS_ROOT}}", TEMPLATE.read_text())

    def test_template_forbids_help_calls(self):
        self.assertIn("never call `--help`", TEMPLATE.read_text())


if __name__ == "__main__":
    unittest.main()
