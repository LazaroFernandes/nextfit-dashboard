from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ContainerSafetyTests(unittest.TestCase):
    def test_container_starts_as_non_root_without_runtime_chown(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        command = next(line for line in dockerfile.splitlines() if line.startswith("CMD "))

        self.assertIn("USER appuser", dockerfile)
        self.assertNotIn("chown", command)
        self.assertNotIn("gosu", dockerfile)

    def test_compose_uses_a_named_volume_instead_of_a_bind_mount(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("catraca-entry-data:/app/data", compose)
        self.assertNotIn("./data:/app/data", compose)
