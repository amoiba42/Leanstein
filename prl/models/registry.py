"""Model registry: LM Studio keys → GGUF files and SHA-256 hashes (NFR-ENV-2)."""
from __future__ import annotations

from pathlib import Path

from prl.config import PATHS, read_json, sha256_file, write_json

MODELS_DIR = Path.home() / ".lmstudio" / "models"

ROLES = {
    "qwen3.5-2b": ("primary", "Qwen3.5", 2.0, "lmstudio-community/Qwen3.5-2B-GGUF"),
    "qwen3.5-4b": ("primary", "Qwen3.5", 4.0, "lmstudio-community/Qwen3.5-4B-GGUF"),
    "gemma-4-e4b-it": ("secondary", "Gemma-4", 4.0, "gemma-4-E4B-it-GGUF"),
    "qwen3.5-9b": ("secondary", "Qwen3.5", 9.0, "lmstudio-community/Qwen3.5-9B-GGUF"),
    "goedel-code-prover-8b": ("specialist", "Goedel-Code-Prover (Qwen3)", 8.0, "mradermacher/Goedel-Code-Prover-8B-GGUF"),
    "qwen3.5-0.8b": ("natural_generator", "Qwen3.5", 0.8, "lmstudio-community/Qwen3.5-0.8B-GGUF"),
}


def find_gguf(repo_hint: str) -> list[Path]:
    name = repo_hint.split("/")[-1].lower()
    out = []
    for p in MODELS_DIR.rglob("*.gguf"):
        if name in str(p.parent).lower() and "mmproj" not in p.name.lower():
            out.append(p)
    return sorted(out)


def build_registry(hash_files: bool = True) -> dict:
    reg = {}
    for key, (role, family, size, repo) in ROLES.items():
        files = find_gguf(repo)
        reg[key] = {"role": role, "family": family, "size_b": size, "repo": repo,
                    "files": [{"path": str(f), "bytes": f.stat().st_size,
                               "sha256": sha256_file(f) if hash_files else None} for f in files]}
    write_json(PATHS.results / "model_registry.json", reg)
    return reg


def load_registry() -> dict:
    p = PATHS.results / "model_registry.json"
    return read_json(p) if p.exists() else {}
