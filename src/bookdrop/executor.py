import shutil
from pathlib import Path

from bookdrop.filing import FilingError, Plan


class Exists(FilingError):
    """A book is already where this one would go."""


class Executor:
    """The one writer under the books root. Nothing else opens a path there for
    writing; a test holds that line."""

    def __init__(self, books_root: Path):
        self.books_root = books_root

    def file(self, plan: Plan) -> Path:
        """Write the plan's directory and files, never over anything that exists.

        Each file is written beside its name and renamed into place, so a reader
        never sees half of one. On any failure everything this call created is
        removed, empty parents included. Raises FilingError when the library
        refuses the write or a book is already there.
        """
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
        except BaseException as error:
            if made_target:
                shutil.rmtree(target, ignore_errors=True)
            # Only if still empty: another book may have arrived beside it.
            for path in reversed(parents):
                try:
                    path.rmdir()
                except OSError:
                    break
            if isinstance(error, OSError):
                raise FilingError(
                    f"The library could not be written to: {error}"
                ) from error
            raise
        return target
