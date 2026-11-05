import shutil
from pathlib import Path

from bookdrop.filing import Plan


class DryRun(Exception):
    """Filing was asked for while dry run is on."""


class Exists(Exception):
    """A book is already where this one would go."""


class Executor:
    """The one writer under the books root. Nothing else opens a path there for
    writing; a test holds that line."""

    def __init__(self, books_root: Path, dry_run: bool):
        self.books_root = books_root
        self.dry_run = dry_run

    def file(self, plan: Plan) -> Path:
        """Write the plan's directory and files, never over anything that exists.

        Each file is written beside its name and renamed into place, so a reader
        never sees half of one. On any failure everything this call created is
        removed, empty parents included.
        """
        if self.dry_run:
            raise DryRun("Dry run is on, so nothing is written to the library.")
        target = self.books_root / plan.directory
        parents: list[Path] = []
        made_target = False
        try:
            for directory in reversed(plan.directory.parents):
                path = self.books_root / directory
                if directory.parts:
                    try:
                        path.mkdir()
                        parents.append(path)
                    except FileExistsError:
                        pass
            try:
                # mkdir, not exists(): it fails if another drop got there first.
                target.mkdir()
            except FileExistsError:
                raise Exists(f"A book is already at {plan.directory}.") from None
            made_target = True
            for name, data in plan.files.items():
                part = target / f".{name}.part"
                part.write_bytes(data)
                part.replace(target / name)
        except BaseException:
            if made_target:
                shutil.rmtree(target, ignore_errors=True)
            # Only if still empty: another book may have arrived beside it.
            for path in reversed(parents):
                try:
                    path.rmdir()
                except OSError:
                    break
            raise
        return target
