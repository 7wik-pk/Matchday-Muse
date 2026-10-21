"""A development cache for the analysis stages: the match pick, the moment and
the fact draft. Re-running a week you have already run reuses them, so a
repeat run makes only the poem and judge calls, while the poem stays fresh.

Entries are keyed on everything that shapes the answer: the stage, the model,
its reasoning effort, the exact prompts and the exact match data. A different
model, a prompt edit or new match data is a miss. Nothing expires: the inputs
are completed matches. Delete the directory to start over.
"""

import hashlib
import os
import tempfile
from pathlib import Path


class AnalysisCache:
    def __init__(self, directory: Path) -> None:
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(*parts: str) -> str:
        return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()

    def get(self, key: str) -> str | None:
        try:
            return (self.dir / f"{key}.json").read_text()
        except OSError:
            return None

    def put(self, key: str, value: str) -> None:
        # Write then rename, so a reader never sees half an entry.
        fd, tmp = tempfile.mkstemp(dir=self.dir, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            f.write(value)
        os.replace(tmp, self.dir / f"{key}.json")
