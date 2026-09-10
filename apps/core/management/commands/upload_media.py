from hashlib import sha256
from pathlib import Path

from django.core.files import File
from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError


def digest(file):
    value = sha256()
    for chunk in iter(lambda: file.read(1024 * 1024), b""):
        value.update(chunk)
    return value.digest()


class Command(BaseCommand):
    help = "Copy local media to configured storage without changing database paths; no deletes or overwrites."

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True)
        parser.add_argument("--apply", action="store_true", help="Without this flag, only inventory the local files.")

    def handle(self, *args, **options):
        root = Path(options["source"]).resolve()
        if not root.is_dir():
            raise CommandError("Source must be an existing directory.")
        copied = existing = total = 0
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise CommandError("Source contains an unsafe linked file.")
            name = path.relative_to(root).as_posix()
            total += 1
            if not options["apply"]:
                continue
            alias = "private" if name.startswith(("invoices/", "payment_slips/")) else "default"
            storage = storages[alias]
            if storage.exists(name):
                with storage.open(name, "rb") as remote, path.open("rb") as local:
                    if digest(remote) != digest(local):
                        raise CommandError("An existing destination differs; stopped without overwriting it.")
                existing += 1
                continue
            with path.open("rb") as local:
                saved = storage.save(name, File(local))
            if saved != name:
                raise CommandError("Storage changed a file name; investigate before switching the website.")
            with storage.open(name, "rb") as remote, path.open("rb") as local:
                if digest(remote) != digest(local):
                    raise CommandError("Uploaded content verification failed.")
            copied += 1
        self.stdout.write(f"Files: {total}; copied and verified: {copied}; already identical: {existing}.")
