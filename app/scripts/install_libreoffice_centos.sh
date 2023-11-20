#!/bin/bash

# exit when any command fails
set -e

# echo an error message before exiting
trap 'echo "\"${last_command}\" command exited with code $?."' EXIT

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  distro=$(cat /etc/os-release | grep "^ID=" | cut -d "=" -f 2 | tr -d '"')
else
  echo "This script does not handle OS $OSTYPE ! Check the README.md for installation instructions."
  exit 1
fi

if [[ "$distro" == "centos" ]]; then
  echo "installing libreoffice on centos..."
  lo_pkg=LibreOffice_7.4.7_Linux_x86-64_rpm.tar.gz
  lo_path=/libreoffice/stable/7.4.7/rpm/x86_64/${lo_pkg}

  OPENDOC_ROOT=$(dirname "$(dirname "$(readlink -f "$0")")")
  APP_LOCATION=${OPENDOC_ROOT}/.apps/libreoffice

  # create directory for libreoffice app
  mkdir -p "${APP_LOCATION}"

  # download and unpack package
  wget https://download.documentfoundation.org/${lo_path} -P "${APP_LOCATION}"
  tar xvzf ${APP_LOCATION}/LibreOffice_7.4.7_Linux_x86-64_rpm.tar.gz --directory "${APP_LOCATION}"

  # unpack rpm files
  for i in ${APP_LOCATION}/LibreOffice_7.4.7.2_Linux_x86-64_rpm/RPMS/*.rpm; do
    rpm2cpio $i | (
      cd $APP_LOCATION
      cpio -id
    )
  done

  # cleanup
  echo "cleaning up..."
  rm -rv ${APP_LOCATION}/LibreOffice_7.4.7.2_Linux_x86-64_rpm/
  rm -v ${APP_LOCATION}/LibreOffice_7.4.7_Linux_x86-64_rpm.tar.gz

  # install unoserver
  echo "pip installing unoserver..."
  wget https://bootstrap.pypa.io/get-pip.py
  ${APP_LOCATION}/opt/libreoffice7.4/program/python get-pip.py
  ${APP_LOCATION}/opt/libreoffice7.4/program/python -m pip install unoserver

  # fix shebangs in unoserver and unoconvert (when install with pip the shebangs get messed up)
  sed -i '1s/python\.bin/python/' ${APP_LOCATION}/opt/libreoffice7.4/program/python-core-3.8.16/bin/unoserver
  sed -i '1s/python\.bin/python/' ${APP_LOCATION}/opt/libreoffice7.4/program/python-core-3.8.16/bin/unoconvert

  # add unoserver and unoconvert to path
  echo "export PATH=${APP_LOCATION}/opt/libreoffice7.4/program/python-core-3.8.16/bin:\$PATH" >>~/.bashrc
  echo "added unoserver and unoconvert to path. To test it, run 'unoserver -h' and 'unoconvert -h'."

else
  echo "this script does not support distro $distro"
  exit 1
fi
