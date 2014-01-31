#!/bin/bash


# This script tries to automate a few of the steps to get a flyscript-portal
# instance installed on a Linux machine.
#
# The basic steps are as follows:
# 1. start in a new directory where everything will be installed
# 2. download a copy of the python tool, "virtualenv"
# 3. create a new virtualenv environment
# 4. get a copy of flyscript-portal from github
# 4a. if "git" is installed, then use "git clone"
# 4b. otherwise, download a zip file from github and unzip it
# 5. install the additional python packages needed for portal
#    from the "requirements.txt" file
# 6. reset the portal, leaving it ready for use as a dev server.
#


START_DIR=`pwd`

mkdir support_files
cd support_files
curl -O https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.10.1.tar.gz
tar xvzf virtualenv-1.10.1.tar.gz
cd $START_DIR

python support_files/virtualenv-1.10.1/virtualenv.py virtualenv
source virtualenv/bin/activate

# clone from github if we have git installed
if hash git 2>/dev/null; then
    git clone https://github.com/riverbed/flyscript-portal.git
else
    curl -L -o flyscript-portal.zip https://github.com/riverbed/flyscript-portal/archive/master.zip
    unzip flyscript-portal.zip
    mv flyscript-portal-master flyscript-portal
fi

cd flyscript-portal
pip install importlib

./bootstrap.py develop

pip install -r requirements.txt


./clean --reset --force


echo "######"
echo ""
echo "Portal installation complete."
echo ""
echo "To run the development server, run the following commands:"
echo "  > source $START_DIR/virtualenv/bin/activate"
echo "  > python manage.py runserver <ipaddress>:8000"
echo "where <ipaddress> is the address other machines will connect to."
echo ""
echo "######"

