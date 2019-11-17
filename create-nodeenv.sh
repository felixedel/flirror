#!/usr/bin/env sh

set -e

pip install $@
nodeenv --python-virtualenv --requirements=css-requirements.txt
