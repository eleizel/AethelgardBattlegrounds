"""Deterministic seeded random wrapper."""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


class SeededRNG:
    """Isolated RNG stream so lobby matches and combat remain reproducible."""

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else random.SystemRandom().randint(1, 2**31 - 1)
        self._rng = random.Random(self.seed)

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def random(self) -> float:
        return self._rng.random()

    def choice(self, seq: Sequence[T]) -> T:
        if not seq:
            raise ValueError("Cannot choose from empty sequence")
        return self._rng.choice(seq)

    def sample(self, seq: Sequence[T], k: int) -> list[T]:
        return self._rng.sample(list(seq), k)

    def shuffle(self, items: list[T]) -> None:
        self._rng.shuffle(items)

    def fork(self, salt: int = 0) -> SeededRNG:
        return SeededRNG(self._rng.randint(1, 2**31 - 1) ^ salt)
