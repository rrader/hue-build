#!/bin/bash

set -e

# build rpms
rm -rf $HOME/rpmbuild/out

sudo yum -y install createrepo git rpm-build mysql-devel openldap-devel python-simplejson sqlite-devel python-setuptools python-devel
sudo easy_install virtualenv boto

BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "=========================="
echo "Building '$BRANCH' branch!"
echo

bash deploy/rpm/build.sh "$BRANCH"

createrepo $HOME/rpmbuild/out
ls $HOME/rpmbuild/out

echo
echo "=========================="
echo "Uploading artefacts to S3"
echo
python build-scripts/upload.py "$BRANCH" "$HOME/rpmbuild/out" build-scripts/aws_credentials.json

rm -rf output
cp -R "$HOME/rpmbuild/out" output