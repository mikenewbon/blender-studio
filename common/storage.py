from storages.backends.s3boto3 import S3Boto3Storage


class S3PublicStorage(S3Boto3Storage):
    querystring_auth = False
