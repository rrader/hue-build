#!/bin/bash

set -e

# FIXME: place path to sandbox-shared here
WORKSPACE="`pwd`"


# Assume environment already prepared.

cd $WORKSPACE
cd deploy/vagrant

rm -f *.ova hyper-v/sandbox.vhd

vagrant up default
bash "export.sh"

# check errors
if [ ! -f *VirtualBox.ova ]; then
    echo "No VirtualBox image" >&2
    exit 1
fi

if [ ! -f *VMware.ova ]; then
    echo "No VMware image" >&2
    exit 1
fi

if [ ! -f hyper-v/sandbox.vhd ]; then
    echo "No Hyper-V vhd" >&2
    exit 1
fi

mkdir -p output
mv *.ova hyper-v/sandbox.vhd output
mv output/sandbox.vhd "output/Hortonworks Sandbox 2.0 Beta Hyper-V.ova"

REMOTE="qe/`date +"%m_%d_%Y"`/"
python build-scripts/upload.py "$REMOTE" "output" build-scripts/aws_credentials.json
