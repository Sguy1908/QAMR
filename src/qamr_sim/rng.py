"""Stable SHA256 namespaces; no Python hash or shared mutable RNG state."""

import hashlib
import json

import numpy as np

STREAMS = ("topology", "traffic", "hardware", "service", "policy", "failures")


def rng(seed: int, stream: str, *key) -> np.random.Generator:
    encoded = json.dumps([seed, stream, *key], separators=(",", ":")).encode()
    entropy = int.from_bytes(hashlib.sha256(encoded).digest()[:16], "little")
    return np.random.default_rng(entropy)
