import os
import sys
import json

import boto
import boto.s3.key

# load credentials from a predefined file
CREDENTIALS = json.load(open(sys.argv[3]))
AWS_ACCESS_KEY_ID = CREDENTIALS['access_key']
AWS_SECRET_ACCESS_KEY = CREDENTIALS['secret_key']
BUCKET_NAME = CREDENTIALS['bucket']


def do_upload(client, path, location='repo/', remote=''):
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
        do_upload(client, "%s/%s" % (path, f), location=location, remote="%s/%s" % (remote, f))


def upload(name='repo', subfolder="/out", local=None):
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
    do_upload(bucket, "%s%s" % (local, subfolder), bucket_location)


def main():
    upload(sys.argv[1], local=sys.argv[2])

if __name__ == '__main__':
    main()
