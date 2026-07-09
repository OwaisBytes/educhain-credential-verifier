"""Part C: Merkle tree built from scratch (no external tree library)."""

from __future__ import annotations

import hashlib
from typing import Any


def _hash_pair(left: str, right: str) -> str:
    combined = (left + right).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


class MerkleTree:
    def __init__(self, leaves: list[str]) -> None:
        if not leaves:
            raise ValueError("Merkle tree requires at least one leaf")
        self.leaves = list(leaves)
        self.layers: list[list[str]] = []
        self.root = self._build()

    def _build(self) -> str:
        layer = list(self.leaves)
        self.layers = [layer]
        while len(layer) > 1:
            next_layer: list[str] = []
            for i in range(0, len(layer), 2):
                left = layer[i]
                right = layer[i + 1] if i + 1 < len(layer) else layer[i]
                next_layer.append(_hash_pair(left, right))
            layer = next_layer
            self.layers.append(layer)
        return layer[0]

    def get_root(self) -> str:
        return self.root

    def get_proof(self, leaf_index: int) -> list[dict[str, str]]:
        proof: list[dict[str, str]] = []
        idx = leaf_index
        for layer in self.layers[:-1]:
            if idx % 2 == 0:
                sibling_idx = idx + 1
                position = "right"
            else:
                sibling_idx = idx - 1
                position = "left"
            if sibling_idx < len(layer):
                proof.append({"hash": layer[sibling_idx], "position": position})
            idx //= 2
        return proof

    @staticmethod
    def verify_proof(leaf_hash: str, proof: list[dict[str, str]], root: str) -> bool:
        current = leaf_hash
        for step in proof:
            sibling = step["hash"]
            if step["position"] == "right":
                current = _hash_pair(current, sibling)
            else:
                current = _hash_pair(sibling, current)
        return current == root

    def changed_path_after_tamper(self, original: MerkleTree, tampered_index: int) -> list[str]:
        path: list[str] = []
        orig_layers = original.layers
        new_layers = self.layers
        idx = tampered_index
        depth = 0
        while depth < len(orig_layers):
            orig_node = orig_layers[depth][idx] if idx < len(orig_layers[depth]) else ""
            new_node = new_layers[depth][idx] if idx < len(new_layers[depth]) else ""
            if orig_node != new_node:
                path.append(f"layer{depth}[{idx}]={new_node[:16]}...")
            idx //= 2
            depth += 1
        return path
