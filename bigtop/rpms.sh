#!/bin/bash

BTBRANCH=$(source HDP_variables.sh &>/dev/null; echo $bigtopbranch)
BRANCH=$(source HDP_variables.sh &>/dev/null; echo $huebranch)
REPODIR="$BTBRANCH/build/hue/rpm/RPMS/x86_64"

echo "Building RPMS for Hue branch '$BRANCH' with bigtop branch '$BTBRANCH'"
echo
echo "=========================="
echo "Prepare environment"
echo

# fix /dev/fd
[ ! -e /dev/fd ] && sudo ln -s /proc/self/fd /dev/fd

sudo yum -y install createrepo git rpm-build redhat-lsb libxml2-devel libxslt-devel java-1.6.0-openjdk-devel mysql-devel openldap-devel python-simplejson sqlite-devel python-setuptools python-devel

WORKSPACE="`pwd`"

MVN_VERSION=3.1.0

cd $HOME
[ ! -f apache-maven-$MVN_VERSION-bin.tar.gz ] && wget http://apache-mirror.telesys.org.ua/maven/maven-3/$MVN_VERSION/binaries/apache-maven-$MVN_VERSION-bin.tar.gz
sudo tar xzf apache-maven-$MVN_VERSION-bin.tar.gz -C /usr/local
cd /usr/local
sudo ln -sf apache-maven-$MVN_VERSION maven 

cd $HOME
pwd
mkdir -p tools/maven tools/jdk64_31
[ ! -e tools/maven/latest ] && ln -sf  /usr/local/maven tools/maven/latest
[ ! -e tools/jdk64_31/latest ] && ln -sf  /usr/lib/jvm/java-1.6.0-openjdk.x86_64 tools/jdk64_31/latest

export M2_HOME=/usr/local/maven
export PATH=${M2_HOME}/bin:${PATH}
export JAVA_HOME=/usr/lib/jvm/java-1.6.0-openjdk.x86_64


echo "=========================="
echo "Build"
echo

rm -rf "$REPODIR"
cd "$WORKSPACE"

BUILD_NUMBER=100 sh bigtop_build.sh hue

echo
echo "DONE!"
echo "=========================="
echo
echo "=========================="
echo "Creating repository..."
echo

createrepo "$REPODIR"

echo "=========================="
echo "Uploading artefacts to S3"
echo

ls -R $REPODIR
python build-scripts/upload.py "bigtop/$1-$BRANCH" "$REPODIR" build-scripts/aws_credentials.json
