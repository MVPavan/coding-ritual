"""Regression checks for shared-policy migration; runs only in temporary repos."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from migrate_claude_to_codex import main


class SharedMigrationTests(unittest.TestCase):
    def make_source(self, repo: Path) -> Path:
        skill = repo / ".claude" / "skills" / "example" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            "---\nname: example\ndescription: Example workflow.\n---\n"
            "Read .claude/project/verification.md and AGENTS.md.\n"
        )
        project = repo / ".claude/project/verification.md"
        project.parent.mkdir(parents=True)
        project.write_text("Shared conventions.\n")
        rule = repo / ".claude" / "rules" / "example.md"
        rule.parent.mkdir(parents=True)
        rule.write_text("A scoped instruction requiring manual routing.\n")
        (repo / "AGENTS.md").write_text("Existing shared policy.\n")
        return skill

    def run_migration(self, repo: Path, *flags: str) -> str:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["migrate", "--repo", str(repo), *flags]), 0)
        return output.getvalue()

    def test_dry_run_leaves_source_and_destination_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            skill = self.make_source(repo)
            before = skill.read_bytes()
            self.run_migration(repo)
            self.assertFalse((repo / ".codex").exists())
            self.assertEqual(skill.read_bytes(), before)

    def test_apply_uses_shared_source_without_generating_policy_copies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            skill = self.make_source(repo)
            before = skill.read_bytes()
            output = self.run_migration(repo, "--apply")
            target = repo / ".codex/skills/example"
            self.assertTrue(target.is_symlink())
            self.assertEqual((target / "SKILL.md").resolve(), skill.resolve())
            self.assertEqual((target / "SKILL.md").read_bytes(), before)
            self.assertFalse((repo / ".codex/project").exists())
            self.assertFalse((repo / ".codex/rules").exists())
            self.assertIn("manual", output.lower())
            self.assertEqual(
                (repo / "AGENTS.md").read_text(), "Existing shared policy.\n"
            )
            skill.write_text(skill.read_text() + "New shared guidance.\n")
            self.assertIn("New shared guidance.", (target / "SKILL.md").read_text())
            self.run_migration(repo, "--apply")
            self.assertTrue(target.is_symlink())

    def test_force_does_not_replace_existing_skill_or_write_through_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            skill = self.make_source(repo)
            target = repo / ".codex/skills/example"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("User-owned destination.\n")
            self.run_migration(repo, "--apply", "--force")
            self.assertEqual(
                (target / "SKILL.md").read_text(), "User-owned destination.\n"
            )
            self.assertIn("Read .claude/project/", skill.read_text())

    def test_command_collision_cannot_overwrite_canonical_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            skill = self.make_source(repo)
            before = skill.read_bytes()
            command = repo / ".claude" / "commands" / "example.md"
            command.parent.mkdir(parents=True)
            command.write_text("A different legacy command.\n")
            self.run_migration(repo, "--apply", "--force")
            self.assertEqual(skill.read_bytes(), before)

    def test_legacy_uppercase_entrypoint_is_linked_without_source_edit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            skill = self.make_source(repo)
            legacy = skill.with_name("SKILL.MD")
            skill.rename(legacy)
            self.run_migration(repo, "--apply")
            target = repo / ".codex/skills/example/SKILL.md"
            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), legacy.resolve())
            self.assertFalse(skill.exists())


if __name__ == "__main__":
    unittest.main()
