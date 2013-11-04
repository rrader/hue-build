#!/bin/bash

set -e

source build-scripts/lib.sh

BTBRANCH=$(source HDP_variables.sh &>/dev/null; echo $bigtopbranch)
BTEXPORT=$(source HDP_variables.sh &>/dev/null; echo $bigtopexport)
BRANCH=$(source HDP_variables.sh &>/dev/null; echo $huebranch)
REPODIR="$BTEXPORT/output/hue"

echo "Building RPMS for Hue branch '$BRANCH' with bigtop branch '$BTBRANCH'"
echo
echo "=========================="
echo "Prepare environment"
echo

sudo apt-get -y install openjdk-6-jdk git lsb-release libxml2-dev libxslt1-dev libmysqld-dev libldap2-dev python-simplejson libsqlite0-dev python-setuptools python-dev libpam0g-dev debhelper curl devscripts libsqlite3-dev libsasl2-dev libkrb5-dev

sudo easy_install boto


WORKSPACE="`pwd`"

MVN_VERSION=3.1.1

cd $HOME
[ ! -f apache-maven-$MVN_VERSION-bin.tar.gz ] && wget http://apache-mirror.telesys.org.ua/maven/maven-3/$MVN_VERSION/binaries/apache-maven-$MVN_VERSION-bin.tar.gz
sudo tar xzf apache-maven-$MVN_VERSION-bin.tar.gz -C /usr/local
cd /usr/local
sudo ln -sf apache-maven-$MVN_VERSION maven 

cd $HOME
pwd
mkdir -p tools/maven tools/jdk64_31
which java
[ ! -e tools/maven/latest ] && ln -sf  /usr/local/maven tools/maven/latest
[ ! -e tools/jdk64_31/latest ] && ln -sf  /usr/lib/jvm/java-1.6.0-openjdk tools/jdk64_31/latest

export M2_HOME=/usr/local/maven
export PATH=${M2_HOME}/bin:${PATH}
export JAVA_HOME=/usr/lib/jvm/java-1.6.0-openjdk


echo "=========================="
echo "Build"
echo

rm -rf "$REPODIR"
cd "$WORKSPACE"

bash bigtop_build.sh hue

echo
echo "DONE!"
echo "=========================="
echo
echo "=========================="
echo "Creating repository..."
echo

rm -rf /tmp/repository
mkdir -p /tmp/repository
cd /tmp/repository
cp "$WORKSPACE/$REPODIR"/*.deb .
dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz
cd -
# createrepo "$REPODIR"

echo "=========================="
echo "Uploading artefacts to S3"
echo

ls -R /tmp/repository

python build-scripts/upload.py "repo/$(get_s3_directory)/$BRANCH/bigtop/$1" /tmp/repository build-scripts/aws_credentials.json

rm -rf output
cp -R /tmp/repository output
