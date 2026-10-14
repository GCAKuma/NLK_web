"""Private files expose an authorized application URL, never a public media URL."""
from django.core.files.storage import FileSystemStorage, storages
from django.urls import reverse


def private_storage():
    return storages["private"]


class PrivateFileSystemStorage(FileSystemStorage):
    def url(self, name):
        return reverse("private_media", kwargs={"name": name})
