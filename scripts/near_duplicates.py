"""Memory-bounded candidate blocking with conservative actual shingle overlap.

This approximate guard supplements exact inference-prefix deduplication. It is
not an exhaustive semantic or paraphrase detector. Caller supplies input_text
(first 2000 characters), and decides whether matches are skipped or retained.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict


def normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def shingles(text: str) -> frozenset[int]:
    """Hash consecutive word triples, retaining facts and numbers unchanged."""
    words = re.findall(r"\w+", text.casefold())
    return frozenset(
        int.from_bytes(
            hashlib.blake2b(" ".join(words[index : index + 3]).encode(), digest_size=8).digest(),
            "big",
        )
        for index in range(len(words) - 2)
    )


class NearDuplicateIndex:
    """Retrieve high-overlap excerpts using bottom-16 fingerprint blocking.

    Candidate retrieval requires two common low-hash shingles, then verifies
    actual Jaccard >= .95 across ALL word triples. Shared boilerplate alone is
    insufficient. Approximate blocking may miss pairs; report this limitation.
    Stored full sets are bounded by the number/size of admitted excerpts, not
    the source archive size. No dense similarity matrices or new dependencies.
    """

    def __init__(self, threshold: float = 0.95) -> None:
        if not 0 < threshold <= 1:
            raise ValueError("Duplicate threshold must be in (0, 1].")
        self.threshold = threshold
        self._exact: dict[str, str] = {}
        self._documents: list[tuple[str, frozenset[int]]] = []
        self._postings: dict[int, list[int]] = defaultdict(list)

    def __len__(self) -> int:
        return len(self._documents)

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha256(normalized_text(text).encode()).hexdigest()

    def add(self, text: str, record_id: str) -> None:
        """Index an accepted/reserved row, preserving the first exact match ID."""
        key = self._key(text)
        if key in self._exact:
            return
        self._exact[key] = record_id
        features = shingles(text)
        document = len(self._documents)
        self._documents.append((record_id, features))
        for fingerprint in sorted(features)[:16]:
            self._postings[fingerprint].append(document)

    def find(self, text: str) -> str | None:
        """Return the earliest high-overlap ID without changing index contents."""
        exact = self._exact.get(self._key(text))
        if exact is not None:
            return exact
        features = shingles(text)
        if len(features) < 2:
            return None
        candidates: Counter[int] = Counter()
        for fingerprint in sorted(features)[:16]:
            candidates.update(self._postings.get(fingerprint, []))
        for document in sorted(candidate for candidate, hits in candidates.items() if hits >= 2):
            record_id, previous = self._documents[document]
            # Upper bound on Jaccard permits a cheap length rejection.
            if (
                min(len(previous), len(features)) / max(len(previous), len(features))
                < self.threshold
            ):
                continue
            overlap = len(previous.intersection(features))
            union = len(previous) + len(features) - overlap
            if union and overlap / union >= self.threshold:
                return record_id
        return None
