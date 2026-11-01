"""Safe pre-launch updater for Git-based KAIRIS installations."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from core.artifact_io import atomic_write_text
from core.config_loader import load_config


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = PROJECT_DIR / "config" / "protocol_config.json"
DEFAULT_STATUS = PROJECT_DIR / "output" / "update_status.json"


def _status(path: Path, state: str, **details: Any) -> None:
    payload = {
        "state": state,
        "checked_at": datetime.now().astimezone().isoformat(),
        **details,
    }
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _git(arguments: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        timeout=120,
    )


def _revision(reference: str = "HEAD") -> str:
    return _git(["rev-parse", reference]).stdout.strip()


def _file_hash(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def update(
    config_path: Path = DEFAULT_CONFIG,
    status_path: Path = DEFAULT_STATUS,
    check_only: bool = False,
    install_dependencies: bool | None = None,
) -> int:
    """Fetch and fast-forward a clean checkout; never overwrite local changes."""
    config = load_config(config_path)
    enabled = bool(config.get("auto_update_enabled", True))
    remote = str(config.get("auto_update_remote", "origin"))
    branch = str(config.get("auto_update_branch", "main"))
    install_deps = (
        bool(config.get("auto_update_install_dependencies", True))
        if install_dependencies is None
        else install_dependencies
    )

    if not enabled:
        _status(status_path, "disabled")
        print("Atualização automática do KAIRIS desativada na configuração.")
        return 0
    if not shutil.which("git") or not (PROJECT_DIR / ".git").is_dir():
        _status(status_path, "not_git_checkout")
        print("Atualização ignorada: esta instalação não é um checkout Git.")
        return 0

    remote_result = _git(["remote", "get-url", remote], check=False)
    if remote_result.returncode != 0:
        _status(status_path, "no_remote", remote=remote, branch=branch)
        print(f"Atualização ignorada: remoto Git '{remote}' não configurado.")
        return 0

    dirty = _git(["status", "--porcelain", "--untracked-files=no"]).stdout.strip()
    if dirty:
        _status(status_path, "local_changes", remote=remote, branch=branch)
        print("Atualização ignorada: existem alterações locais versionadas.")
        return 0

    old_revision = _revision()
    lock_path = PROJECT_DIR / "requirements.lock"
    old_lock_hash = _file_hash(lock_path)
    try:
        _git(["fetch", "--quiet", remote, branch])
    except (OSError, subprocess.SubprocessError) as error:
        _status(
            status_path,
            "network_error",
            remote=remote,
            branch=branch,
            revision=old_revision,
            detail=str(error),
        )
        print("Não foi possível consultar atualizações; iniciando a versão local.")
        return 0

    remote_reference = f"{remote}/{branch}"
    remote_revision = _revision(remote_reference)
    if old_revision == remote_revision:
        _status(status_path, "up_to_date", revision=old_revision, remote=remote, branch=branch)
        print(f"KAIRIS já está atualizado ({old_revision[:8]}).")
        return 0
    if check_only:
        _status(
            status_path,
            "update_available",
            revision=old_revision,
            available_revision=remote_revision,
            remote=remote,
            branch=branch,
        )
        print(f"Atualização disponível: {old_revision[:8]} → {remote_revision[:8]}.")
        return 0

    ancestor = _git(["merge-base", "--is-ancestor", old_revision, remote_reference], check=False)
    if ancestor.returncode != 0:
        _status(
            status_path,
            "diverged",
            revision=old_revision,
            available_revision=remote_revision,
            remote=remote,
            branch=branch,
        )
        print("Atualização ignorada: o histórico local divergiu do repositório remoto.")
        return 0

    try:
        _git(["merge", "--ff-only", remote_reference])
        new_revision = _revision()
        dependencies_changed = old_lock_hash != _file_hash(lock_path)
        if dependencies_changed and install_deps:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(lock_path)],
                cwd=PROJECT_DIR,
                check=True,
            )
    except (OSError, subprocess.SubprocessError) as error:
        _status(
            status_path,
            "update_failed",
            previous_revision=old_revision,
            remote=remote,
            branch=branch,
            detail=str(error),
        )
        print(f"A atualização do KAIRIS falhou: {error}", file=sys.stderr)
        return 2

    _status(
        status_path,
        "updated",
        previous_revision=old_revision,
        revision=new_revision,
        remote=remote,
        branch=branch,
        dependencies_updated=bool(dependencies_changed and install_deps),
    )
    print(f"KAIRIS atualizado: {old_revision[:8]} → {new_revision[:8]}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--check-only", action="store_true", help="Consultar sem aplicar")
    parser.add_argument("--no-deps", action="store_true", help="Não sincronizar requirements.lock")
    args = parser.parse_args()
    return update(
        args.config.resolve(),
        args.status.resolve(),
        check_only=args.check_only,
        install_dependencies=False if args.no_deps else None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
