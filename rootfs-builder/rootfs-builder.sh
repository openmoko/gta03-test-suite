#!/bin/sh
# COPYRIGHT: Openmoko Inc. 2008
# LICENSE: GPL Version 2 or later
# DESCRIPTION: Build a root filesystem from packages
# AUTHOR: Christopher Hall <hsw@openmoko.com>


# This script is just a simple wrapper around opkg that does an
# initial setup so opkg can run.  The script ensures the correct
# options on the opkg command so that packages do not get installed in
# the root of the host system

# defaults

FEED_SECTION_LIST='all armv4t om-gta02'

URL=http://downloads.openmoko.org/repository/testing
#URL="file://${HOME}/oe/build/tmp/deploy/glibc/opk"

OPKG_PROGRAM=/usr/local/openmoko/arm/bin/opkg-cl
#OPKG_PROGRAM=${HOME}/testing/opkg/build/src/opkg-cl

# path passed to any scripts run by opkg
RESTRICTED_PATH=/bin:/usr/bin


# start of script

usage()
{
  [ -n "$1" ] && echo error: $*
  echo
  echo usage: $(basename "$0") '<options>'
  echo '  --url=http://path          where to get the initial package list'
  echo '                             default:' ${URL}
  echo '  --init                     initialise empty root directory (from url)'
  echo '  --list                     show available packages'
  echo '  --list-installed           show packages already installed'
  echo '  --install <packages...>    install some packages'
  echo '  --devices                  create static device files (prefers minimal table)'
  echo '  --devices-normal           prefer normal table (if avaliable)'
  echo '  --remove <packages...>     remove some packages'
  echo '  --tar=archive.tar[.bz2]    create a tar of the rootfs [optional]'
  echo '  --path=<path:path...>      restricted path fo opkg'
  echo
  echo notes:
  echo '  --init can be used to change the url to a different repository'
  echo '         even after some pachages have been installed'
  echo
  echo examples:
  echo '  '$(basename "$0") --rootfs=/path/to/myroot --init --url=${URL}
  echo '  '$(basename "$0") --rootfs=/path/to/myroot --list
  echo '  '$(basename "$0") --rootfs=/path/to/myroot --install --path=/restricted/bin task-openmoko-linux curl ruby
  echo '  '$(basename "$0") --rootfs=/path/to/myroot --devices
  echo '  '$(basename "$0") --rootfs=/path/to/myroot --list-installed
  exit 1
}


# display a command an ask for permission to sudo it
# if already under sudo the just run the command
REAL_SUDO()
{
  if [ -z "${SUDO_UID}" -o -z "${SUDO_GID}" ]
  then
    echo SUDO: "$@"
    "$@"
  else
    "$@"
  fi
}


# simulation of sudo using fakeroot
SUDO()
{
  local load=''
  if [ -e "${FakerootDatabase}" ]
  then
    fakeroot -s "${FakerootDatabase}" -i "${FakerootDatabase}" -- "$@"
  else
    fakeroot -s "${FakerootDatabase}" -- "$@"
  fi
}

# run opkg passing certail predefined options
OPKG()
{
  local rc=0
  if [ -n "${CacheDirectory}" ]
  then
    SUDO ${OPKG_PROGRAM} -offline "${rootfs}" --offline-path "${RESTRICTED_PATH}" --cache "${CacheDirectory}" "$@"
    rc="$?"
  else
    SUDO ${OPKG_PROGRAM} -offline "${rootfs}" --offline-path "${RESTRICTED_PATH}" "$@"
    rc="$?"
  fi
  return "${rc}"
}


# build the directory to for the root fs
makeroot()
{
  local rootfs url frdb
  rootfs="$1"; shift
  url="$1"; shift
  frdb="$1"; shift

  local conf ConfDir
  conf="${rootfs}/etc/opkg.conf"
  ConfDir="${rootfs}/etc/opkg"

  rm -f "${frdb}"

  SUDO mkdir -p "${rootfs}/etc/opkg"
  SUDO mkdir -p "${rootfs}/usr/lib/opkg"

  for item in ${FEED_SECTION_LIST}
  do
    SUDO echo src/gz om-dev-${item} "${url}/${item}" > "${ConfDir}/${item}-feed.conf"
  done

  local arch="${ConfDir}/arch.conf"

  # only create the arch.conf if it does not already exist
  if [ ! -e "${arch}" ]
  then
    SUDO cat > "${arch}" <<EOF
arch all 1
arch any 6
arch noarch 11
arch arm 16
arch armv4t 21
arch om-gta02 26
EOF
  fi
}
  

# start of main program

[ -n "${SUDO_UID}" -o -n "${SUDO_GID}" ] && usage just do not run this with sudo or it will corrupt the host system


# locate programs

[ -x "${OPKG_PROGRAM}" ] || usage unable to locate opkg binary, check installation of Openmoko toolchain

[ -z "$(which fakeroot)" ] && usage install the fakeroot package


# check opkg version

version=$("${OPKG_PROGRAM}" --version | awk '{print $3}')
case "${version}" in
  0.1.0|0.1.1|0.1.2|0.1.3|0.1.4|0.1.5)
    usage opkg version ${vesion} is too old
    ;;
  0.1.*)
    ;;
  *)
    usage opkg version ${vesion} is not tested/supported yet
    ;;
esac

verbose=0
rootfs=/tmp/rootfs
FakerootDatabase=/tmp/rootfs.frdb

makedevs_dir="$(readlink -f "$(dirname "$0")")/makedevs"
command=null
url="${URL}"
archive=
CacheDirectory=

while [ $# -ne 0 ]
do
  arg="$1"
  case "${arg}" in

    --verbose)
      verbose=1
      ;;
    --rootfs=*)
      rootfs="$(readlink -m "${arg#*=}")"
      ;;
    --path=*)
      RESTRICTED_PATH="${arg#*=}"
      ;;
    --cache=*)
      CacheDirectory="$(readlink -m "${arg#*=}")"
      [ -d "${CacheDirectory}" ] || usage cache directory: ${CacheDirectory} does not exist
      ;;
    --url=*)
      url="${arg#*=}"
      ;;
    --tar=*)
      archive="${arg#*=}"
      ;;
    --install)
      [ X"${command}" = X"null" ] || usage conflicting commands
      command=install
      ;;
    --dev*-n*)
      [ X"${command}" = X"null" ] || usage conflicting commands
      command=devices
      ;;
    --dev*)
      [ X"${command}" = X"null" ] || usage conflicting commands
      command=devices-minimal
      ;;
    --remove)
      [ X"${command}" = X"null" ] || usage conflicting commands
      command=remove
      ;;
    --configure)
      [ X"${command}" = X"null" ] || usage conflicting commands
      command=configure
      ;;
    --init*)
      [ X"${command}" = X"null" ] || usage conflicting commands
      command=init
      ;;
    --list)
      [ X"${command}" = X"null" ] || usage conflicting commands
      command=list
      ;;
    --list-installed)
      [ X"${command}" = X"null" ] || usage conflicting commands
      command=list_installed
      ;;
    -h|--help)
      usage help message
      ;;
    -*)
      usage invalid argument: ${arg}
      ;;
    *)
      break
      ;;
  esac
  shift
done

FakerootDatabase="${rootfs}.frdb"
echo rootfs = ${rootfs}
echo url = ${url}

[ X"${command}" != X"init" -a ! -d "${rootfs}" ] && usage root directory not inititilaised


# process command
case "${command}" in

  init)
    makeroot "${rootfs}" "${url}" "${FakerootDatabase}"
    OPKG update
    ;;

  list*)
    OPKG "${command}"
    ;;

  devices*)
    MKDEV=$(make -s -C "${makedevs_dir}" program-name)
    MINIMAL_DEVICE_TABLE=$(make -s -C "${makedevs_dir}" device-table-name)
    INTERNAL_DEVICE_TABLE="${rootfs}/etc/device_table"

    case "${command}" in
      devices-minimal)
        device_table="${MINIMAL_DEVICE_TABLE}"
        ;;
      *)
        device_table="${INTERNAL_DEVICE_TABLE}"
        ;;
    esac

    if [ ! -x "${MKDEV}" ]
    then
      make -C "${makedevs_dir}" all
    fi

    if [ ! -f "${device_table}" ]
    then
      if [ -f "${MINIMAL_DEVICE_TABLE}" ]
      then
        device_table="${MINIMAL_DEVICE_TABLE}"
      elif [ -f "${INTERNAL_DEVICE_TABLE}" ]
      then
        device_table="${INTERNAL_DEVICE_TABLE}"
      else
        usage internal error: no device tables found
      fi
    fi

    echo using program: ${MKDEV}
    echo using device table: ${device_table}

    SUDO rm -f "${rootfs}/dev/"*
    SUDO ${MKDEV} --root="${rootfs}" --devtable="${device_table}"
    # --squash           Squash permissions and owners making all files be owned by root
    ;;

  install)
    OPKG update

    for item in "$@"
    do
      OPKG -force-reinstall -force-defaults "${command}" "${item}"
    done
    ;;

  remove|configure)
    for item in "$@"
    do
      OPKG -force-depends "${command}" "${item}"
    done
    ;;

  null)
    [ -z "${archive}" ] && usage no command has been specified
    ;;

  *)
    usage unsupported command: ${command}
    ;;
esac

if [ -n "${archive}" ]
then
  echo creating archive of the root file system: ${archive}

  local flag=

  [ X"${archive}" != X"${archive%.bz2}" ] && flag=j
  [ X"${archive}" != X"${archive%.gz}" ] && flag=z

  SUDO tar -c${flag}f "${archive}" -C "${rootfs}" .

fi