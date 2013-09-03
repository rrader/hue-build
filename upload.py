import os
import sys
import json

import boto
import boto.s3.key

# arguments:
#   1: bucket key prefix
#   2: local folder
#   3: s3 credentials json file

# load credentials from a predefined file
CREDENTIALS = json.load(open(sys.argv[3]))
AWS_ACCESS_KEY_ID = CREDENTIALS['access_key']
AWS_SECRET_ACCESS_KEY = CREDENTIALS['secret_key']
BUCKET_NAME = CREDENTIALS['bucket']


def _upload(client, path, location='repo/', remote=''):
    if os.path.isfile(path):
        print " ---  put %s to %s" % (path, location + remote)
        k = boto.s3.key.Key(client)
        k.key = location + remote
        k.set_contents_from_filename(path)
        k.make_public()
        return

    files_in_dir = os.listdir(path)
    for f in files_in_dir:
        print f
        _upload(client, "%s/%s" % (path, f), location=location, remote="%s/%s" % (remote, f))


def upload(name='repo', local=None):
    "upload to s3 rpms. args: s3dir"
    conn = boto.connect_s3(AWS_ACCESS_KEY_ID,
                           AWS_SECRET_ACCESS_KEY)
    bucket = conn.get_bucket(BUCKET_NAME)

    print "clean target location..."
    bucket_location = name
    for key in bucket.list(bucket_location):
        print " ---  delete " + key.key
        key.delete()

    if not local:
        local = name
    _upload(bucket, local, bucket_location)


def main():
    upload(sys.argv[1], local=sys.argv[2])

if __name__ == '__main__':
    main()
