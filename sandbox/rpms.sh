#!/bin/bash

# $1 - sandbox-shared branch name

# updating sources
# if [ ! -e /home/sandbox/rpm-shared/ ]; then
# 	cd $HOME
# 	git clone git@github.com:/hortonworks/sandbox-shared.git rpm-shared
# fi

# cd $HOME/rpm-shared/
# git reset --hard HEAD^^ && git fetch && git checkout "$1" && git pull

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
python build-scripts/sandbox/upload.py "$BRANCH" "$HOME/rpmbuild" build-scripts/sandbox/aws_credentials.json
