"""RegistryConfig; the repo and data roots are resolved from this file."""

from __future__ import annotations

from pathlib import Path

from curation.registry.models import StrictModel

REPO_ROOT = Path(__file__).resolve().parents[2]
HL_DIR = REPO_ROOT / "harness_lifecycle"


class RegistryConfig(StrictModel):
    repo_root: Path
    registry_dir: Path
    ledger_dir: Path
    manifest_path: Path
    skill_records_dir: Path
    references_dir: Path
    index_path: Path
    trait_definitions_path: Path
    traits_dir: Path
    skills_path: Path
    traits_md_path: Path
    catalogs_dir: Path
    skills_dir: Path
    our_harness_root: Path
    codex_root: Path
    plugins_glob: str = "mvp-harness/plugins/*"
    # Rounds sealed before traits existed (§5 "Awaiting trait ruling"). Closed:
    # a round sealed after the migration is never added.
    pre_trait_rounds: frozenset[str] = frozenset(
        {"2026-10-14-migration", "2026-10-14-owner-review"}
    )

    @property
    def reviews_dir(self) -> Path:
        """Report files (stages-design §Report file)."""
        return self.registry_dir / "reviews"

    @property
    def trait_policy_path(self) -> Path:
        """Standing stances on traits (stages-design §Trait policy)."""
        return self.registry_dir / "trait-policy.yaml"

    @property
    def trait_sharing_path(self) -> Path:
        """Why our skills share a trait (stages-design §Shared traits)."""
        return self.registry_dir / "trait-sharing.yaml"

    @property
    def playbooks_dir(self) -> Path:
        """Our playbooks, reached only through the router (unit-kinds B1)."""
        return self.skills_dir / "mvp-mode" / "playbooks"

    @property
    def steps_md_path(self) -> Path:
        """The generated step index (unit-kinds St2)."""
        return self.registry_dir / "STEPS.md"

    @property
    def guide_path(self) -> Path:
        """The prompting guide whose rule IDs adopt rows cite (2.9)."""
        return self.repo_root / "harness_lifecycle" / "prompting-guides" / "GUIDE.md"

    @classmethod
    def default(cls) -> RegistryConfig:
        registry_dir = HL_DIR / "registry"
        return cls(
            repo_root=REPO_ROOT,
            registry_dir=registry_dir,
            ledger_dir=registry_dir / "ledger",
            manifest_path=registry_dir / "ledger" / "MANIFEST.json",
            skill_records_dir=registry_dir / "skill-records",
            references_dir=registry_dir / "references",
            index_path=registry_dir / "INDEX.md",
            trait_definitions_path=registry_dir / "trait-definitions.yaml",
            traits_dir=registry_dir / "traits",
            skills_path=registry_dir / "skills.yaml",
            traits_md_path=registry_dir / "TRAITS.md",
            catalogs_dir=HL_DIR / "catalogs",
            skills_dir=REPO_ROOT / ".claude" / "skills",
            our_harness_root=REPO_ROOT / ".claude",
            codex_root=REPO_ROOT / ".codex",
        )


def _rel(cfg: RegistryConfig, path: Path) -> str:
    try:
        return str(path.relative_to(cfg.registry_dir))
    except ValueError:
        return str(path)
