"""Resolve one named execution grant set for mounts and runner translations."""

from pathlib import Path

from workflow_interpreter.contracts.execution import (
    MSG_CODEX_IN_REPO,
    MSG_POLICY_MISMATCH,
    MSG_PRIVATE_GRANTS,
    ExecutionGrants,
    ExecutionPolicy,
    ExecutionProfileName,
    RunnerName,
    ToolNetwork,
    policy_for,
)
from workflow_interpreter.profiles.errors import UnsupportedOptionError
from workflow_interpreter.supervisor.errors import SandboxPathRefused
from workflow_interpreter.supervisor.profile import TaskSpec
from workflow_interpreter.supervisor.sandbox import (
    GIT_ENTRY,
    SandboxPlan,
    worktree_git_write_roots,
)

__all__ = [
    "ExecutionGrants",
    "ExecutionPolicy",
    "ExecutionProfileName",
    "ToolNetwork",
    "resolve_grants",
]


def resolve_grants(task: TaskSpec, plan: SandboxPlan, runner: str) -> ExecutionGrants:
    """Bind named policy to this activation's exact, nonredirected private paths."""
    runner_name = RunnerName.from_profile(runner)
    policy = task.execution_policy
    if policy is None or task.execution_profile is None:
        raise SandboxPathRefused(MSG_POLICY_MISMATCH)
    expected = policy_for(task.execution_profile, runner_name)
    if policy != expected or task.writes != expected.writes:
        raise SandboxPathRefused(
            f"{MSG_POLICY_MISMATCH}: pinned={policy.model_dump_json()}; "
            f"runner={runner_name.value}, expected={expected.model_dump_json()}; "
            f"task writes={task.writes}"
        )
    checkout = Path(task.checkout_read_root or task.cwd)
    channels = Path(task.channels.outcome_file).parent
    scratch = Path(task.channels.scratch_dir or channels / "scratch")
    cache = plan.toolchain_cache[0]
    activation = channels.parent
    private = (channels, scratch, cache)
    if (
        any(
            not path.is_absolute() or path.resolve() != path
            for path in (checkout, *private)
        )
        or channels != activation / "channels"
        or not scratch.is_relative_to(channels)
        or cache != activation / "toolchain" / "uv-cache"
        or any(
            path.is_relative_to(checkout) or checkout.is_relative_to(path)
            for path in private
        )
    ):
        raise SandboxPathRefused(MSG_PRIVATE_GRANTS)
    if not policy.writes and (plan.grants or plan.git_rw):
        raise SandboxPathRefused(MSG_POLICY_MISMATCH)
    if policy.writes and runner_name is RunnerName.CODEX:
        if (checkout / GIT_ENTRY).is_dir():
            raise UnsupportedOptionError(
                MSG_CODEX_IN_REPO.format(node=task.node, checkout=checkout)
            )
        worktree_git_write_roots(checkout, task.root_id)
    cwd = (
        channels if runner_name is RunnerName.CODEX and not policy.writes else checkout
    )
    return ExecutionGrants(
        policy=policy,
        checkout_read_root=str(checkout),
        process_cwd=str(cwd),
        read_only_roots=tuple(map(str, plan.ro_roots)),
        checkout_write_dirs=tuple(map(str, plan.grants)),
        git_dirs=tuple(map(str, plan.git_rw)),
        channels=str(channels),
        scratch=str(scratch),
        private_cache=str(cache),
        read_only_pins=tuple(map(str, plan.ro_pins)),
    )
