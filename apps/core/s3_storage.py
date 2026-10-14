from django.urls import reverse
from storages.backends.s3 import S3Storage


class PrivateS3Storage(S3Storage):
    querystring_auth = True
    querystring_expire = 60
    default_acl = None

    def url(self, name, **kwargs):
        return reverse("private_media", kwargs={"name": name})

    def signed_url(self, name):
        return super().url(name, expire=60)
