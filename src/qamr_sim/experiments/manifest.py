import hashlib
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path

from qamr_sim.rng import STREAMS

ROOT = Path(__file__).resolve().parents[3]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity(config):
    files = []
    for folder in ("src", "dashboard", "configs", "docs"):
        files.extend(
            p
            for p in (ROOT / folder).rglob("*")
            if p.is_file() and p.suffix in (".py", ".yaml", ".md")
        )
    files += [ROOT / "pyproject.toml", ROOT / "requirements.lock"]
    code = hashlib.sha256()
    for file in sorted(files):
        if file.exists():
            code.update(str(file.relative_to(ROOT)).encode())
            code.update(file.read_bytes())
    paper = ROOT / "docs/paper/qamr.pdf"
    versions = dict(
        sorted(
            (package.metadata["Name"], package.version)
            for package in importlib.metadata.distributions()
        )
    )
    cfg = config.model_dump(mode="json")
    return dict(
        config_hash=digest(json.dumps(cfg, sort_keys=True).encode()),
        code_hash=code.hexdigest(),
        paper_checksum=digest(paper.read_bytes()) if paper.exists() else None,
        versions=versions,
        python=platform.python_version(),
    )


def manifest(config):
    ident = identity(config)

    def git(*args):
        result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None

    return dict(
        schema_version=1,
        **ident,
        commit=git("rev-parse", "HEAD"),
        dirty_state=git("status", "--porcelain"),
        dirty_state_hash=ident["code_hash"],
        seed=config.seed,
        topology_seed=config.topology_seed,
        rng_derivation="SHA256 JSON [seed, namespace, *key], first 128 bits little-endian, NumPy PCG64",
        streams=list(STREAMS),
        profile=config.profile,
        assumptions=(ROOT / "docs/assumptions.md").read_text()
        if (ROOT / "docs/assumptions.md").exists()
        else "",
    )
