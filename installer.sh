#!/bin/sh
# COPYRIGHT: Openmoko Inc. 2008
# LICENSE: GPL Version 2 or later
# DESCRIPTION: A simple installer for test images
# AUTHOR: Christopher Hall <hsw@openmoko.com>


# An interactive script that controls the root file system builder and
# allow for building QI and the kernel.  As there are already exiting
# scripts in QI and kernel directories this script just uses them.
# The intention is to have a single script that can format the SD
# Card, install QI, kernel and root file system and browse the result.

BuildDirectory=$(readlink -m tmp)
ConfigurationFile=$(readlink -m .installerrc)


# configuration
# =============

# basic settings
StageDirectory="${BuildDirectory}/rootfs"

MountPoint="${BuildDirectory}/mnt"
MountPointTag="${MountPoint}/.not_mounted_yet"

RootFSArchive="${BuildDirectory}/rootfs.tar.bz2"

PLATFORM=om-3d7k
URL=http://downloads.openmoko.org/repository/testing

# set to YES to completely remove the build directory before other
# actions
# override by command line option --clean / --no-clean
clean="NO"

# format the SD Card if this is set to YES
# override by command line option --format / --no-format
format="NO"

# enable prompting for sudo commands
# override by command line option --prompt / --no-prompt
SudoPrompt="YES"

# keep authorisation for sudo
# override by command line option --keep / --no-keep
KeepAuthorisation="NO"

# location of the cache directory
CacheDirectory="${BuildDirectory}/cache"

# install by default
# override by command line option --install / --no-install
InstallToSDCard="YES"

# SD Card info (assumed to be in /dev)
SDCardDevice="sdb"
SDCardPartition="2"

# Path to the QI directory and its associated files
QiDirectory="$(readlink -m ../qi)"
QiInstaller="6410-partition-sd.sh"
QiImage="image/qi-s3c6410-"

# where to obtain kernel
KernelDirectory="$(readlink -m ../kernel)"
KernelImage="uImage-$(echo ${PLATFORM} | tr a-z- A-Z_).bin"

# how to run the rootfs builder
RootFSBuilderDirectory="$(readlink -m rootfs-builder)"
RootFSBuilder="${RootFSBuilderDirectory}/rootfs-builder.sh"

# path for pre/post package scripts
RestrictedPath="${RootFSBuilderDirectory}/restricted:/bin:/usr/bin"

# the database for fakeroot must be the same as the one used by
# rootfs-builder.sh
FakerootDatabase="${StageDirectory}.frdb"

# type of image
ReplaceKernel="NO"
KernelDirectory="$(readlink -m ../kernel)"
KernelImage="uImage-OM_3D7K.bin"

# provide a hook for the config file to adjust things after command line
# arguments have been processed; set to the name of a shell function
PostHook=

# End of configuration
# ====================

# just in case we want to override any of the above
# read in the configuration file
[ -e "${ConfigurationFile}" ] && . "${ConfigurationFile}"


# functions

usage()
{
  [ -n "$1" ] && echo error: $*
  echo
  echo usage: $(basename "$0") '<options>'
  echo '  --clean      Completely remove build directory and package cache'
  echo '  --format     Erase and recreate SD Card filesystems'
  echo '  --prompt     Ask yes/no before sudo'
  echo '  --keep       Keep sudo authorisation'
  echo '  --kernel     Replace the packaged kernel with a local one'
  echo '  --gtaXX      Set the platform'
  echo '  --om-XXXX    Set the platform'
  echo '  --install    Install to SD Card'
  echo '  --no-XXX     Turn off an option'
  echo 'note: options override configuration file ('${ConfigurationFile}')'
  exit 1
}


INFO()
{
  echo INFO: $*
}


ERROR()
{
  echo ERROR: $*
  exit 1
}


AskYN()
{ 
  local yorn junk rc
  if [ X"${SudoPrompt}" != X"YES" ]
  then
    # always assume yes if not prompting
    return 0
  fi
  while read -p "$* [y/n]? " yorn junk
  do
    case "${yorn}" in
      [yY]|[yY][eE][sS])
        return 0
        ;;
      [nN]|[nN][oO])
        return 1
        ;;
      *)
        echo Unrecognised response: ${yorn}
        ;;
    esac
  done
  return 1
}


SudoReset()
{
  if [ X"${KeepAuthorisation}" != X"YES" ]
  then
    sudo -K
  fi
}


# display a command and ask for permission to sudo it
# if already under sudo then just run the command
SUDO()
{
  if [ -z "${SUDO_UID}" -o -z "${SUDO_GID}" ]
  then
    echo SUDO: "$@"

    SudoReset
    if AskYN Are you really sure running this as root
    then
      sudo "$@"
    else
      echo The command was skipped
    fi
    SudoReset
  else
    "$@"
  fi
}


FakeRoot()
{
  local load=''
  if [ -e "${FakerootDatabase}" ]
  then
    fakeroot -s "${FakerootDatabase}" -i "${FakerootDatabase}" -- "$@"
  else
    fakeroot -s "${FakerootDatabase}" -- "$@"
  fi
}


RBLD_basic()
{
  ${RootFSBuilder} --url="${URL}" --platform="${PLATFORM}" --rootfs="${StageDirectory}" --path="${RestrictedPath}" "$@"
}


RBLD()
{
  local rc=0
  local cache
  if [ -n "${CacheDirectory}" -a -d "${CacheDirectory}" ]
  then
    RBLD_basic --cache="${CacheDirectory}" "$@"
    rc="$?"
  else
    RBLD_basic "$@"
    rc="$?"
  fi

  [ "${rc}" -ne 0 ] && usage Rooot Builder script failed
}


BuildRootFileSystem()
{
  rm -f "${FakerootDatabase}"
  [ -n "${StageDirectory}" ] && rm -rf "${StageDirectory}"

  RBLD --init
  RBLD --install task-openmoko-linux
  RBLD --device-minimal

  RBLD --remove exquisite
  RBLD --remove exquisite-themes
  RBLD --remove exquisite-theme-freerunner

  # install some additional apps
  #RBLD --install python-lang

  RBLD --install i2c-tools

  # add the test suite
  RBLD --install om-test-suite
  RBLD --install om-test-shell
}


SDCardMounted()
{
  mount | grep -q -s "/dev/${SDCardDevice}"
  return "$?"
}


UnmountSDCard()
{
  if SDCardMounted
  then
    SUDO umount  "/dev/${SDCardDevice}"* "${MountPoint}"
    [ -e "${MountPointTag}" ] || ERROR unmount has failed
  fi
  return 0
}


MountSDCard()
{
  local rc
  if ! SDCardMounted
  then
    [ ! -e "${MountPointTag}" ] && ERROR tag missing from mount point
    SUDO mount  "/dev/${SDCardDevice}${SDCardPartition}" "${MountPoint}"
    rc="$?"
    [ -e "${MountPointTag}" ] && ERROR mount has failed - turn off automounting
    return "${rc}"
  else
    [ -e "${MountPointTag}" ] && ERROR mount has failed - turn off automounting
  fi
  return 0
}


# temporary until we have a package
GetTheKernel()
{
  (
    cd "${KernelDirectory}" || ERROR cannot cd to: ${KernelDirectory}

    cp -p "${KernelImage}" "${StageDirectory}/boot/" || ERROR failed to copy the kernel

    env INSTALL_MOD_PATH="${StageDirectory}" make ARCH=arm modules_install || ERROR failed to install modules
    )
  if [ $? -ne 0 ]
  then
    ERROR Install kernel failed
  fi
}



# Fixes any broken OE installed files
ApplyFixes()
{
  # common fixes
  FixBinTrue

  # platform specific fixes
  case "${PLATFORM}" in
    [gG][tT][aA]02)
      #FixGTA02
      ;;

    [oO][mM][-_]3[dD]7[kK])
      #OM_3D7K
      ;;
  esac
}


# if trux is a symlink to busybox replace it by an empty file
# this so that things that symlink to true do not cause
# busybox applet not found (or worse errors
FixBinTrue()
{
  (
    # if true is not symlinked, skip changes
    [ -L "${StageDirectory}/bin/true" ] || exit 0

    FakeRoot rm -f "${StageDirectory}/bin/true"
    FakeRoot touch "${StageDirectory}/bin/true"
    FakeRoot chown 0:0 "${StageDirectory}/bin/true"
    FakeRoot chmod 755 "${StageDirectory}/bin/true"

    exit "$?"
    )
  if [ $? -ne 0 ]
  then
    ERROR FixBinTrue failed
  fi
}


InstallQi()
{
  local action local qi card list
  action="$1"; shift

  case "${action}" in
    [nN][oO]*)
      action=no-format
      ;;
    *)
      action=''
      ;;
  esac

  list='sdhc sd'

  UnmountSDCard || exit 1

  qi=$(ls -1 "${QiDirectory}/${QiImage}"* | head -n 1)

  INFO qi = ${qi}

  for card in ${list}
  do
    SUDO "${QiDirectory}/${QiInstaller}" "${SDCardDevice}" "${card}" "${qi}" "${action}"
    action=no-format
  done
}


InstallRootFileSystem()
{
  if [ -f "${RootFSArchive}" ]
  then
    (
      MountSDCard || ERROR failed to properly mount SD Card

      SUDO tar xf "${RootFSArchive}" -C "${MountPoint}/"
      rc="$?"

      echo
      echo Boot directory:
      ls -l "${MountPoint}/boot"

      echo
      echo Console:
      grep '^S:' "${MountPoint}/etc/inittab"

      echo
      UnmountSDCard || true

      exit "$?"
    )
    if [ $? -ne 0 ]
    then
      ERROR install Root FS failed
    fi
  else
    ERROR Missing rootfs archive '(not built yes?)'
  fi
}


YesOrNo()
{
  local _tag _var
  _tag="$1"; shift
  _var="$1"; shift

  case "${_tag}" in
    -no-*|--no-*)
      eval "${_var}"=\"NO\"
      ;;
    *)
      eval "${_var}"=\"YES\"
      ;;
  esac
}


# main program
# ============

while [ $# -gt 0 ]
do
  arg="$1"; shift
  case "${arg}" in
    --clean|--no-clean)
      YesOrNo "${arg}" clean
      ;;
    --format|--no-format)
      YesOrNo "${arg}" format
      ;;
    --prompt|--no-prompt)
      YesOrNo "${arg}" SudoPrompt
      ;;
    --keep|--no-keep)
      YesOrNo "${arg}" KeepAuthorisation
      ;;
    --install|--no-install)
      YesOrNo "${arg}" InstallToSDCard
      ;;
    --gta[0][12])
      PLATFORM="${arg#--}"
      ;;
    --om-*)
      PLATFORM="${arg#--}"
      ;;
    -h|--help)
      usage
      ;;
    --)
      break
      ;;
    -*)
      usage unrecognised option ${arg}
      ;;
    *)
      break
      ;;
  esac
done

#run the hook after command line arguments have been processed
[ -n "${PostHook}" -a -n "$(typeset -F "${PostHook}")" ] && ${PostHook}

UnmountSDCard

if [ X"${clean}" = X"YES" -a -d "${BuildDirectory}" ]
then
  rm -rf "${BuildDirectory}"
fi

mkdir -p "${BuildDirectory}" || usage failed to create ${BuildDirectory}
mkdir -p "${StageDirectory}" || usage failed to create ${StageDirectory}
mkdir -p "${CacheDirectory}" || usage failed to create ${StageDirectory}
mkdir -p "${MountPoint}" || usage failed to create ${MountPoint}
mkdir -p "${MountPointTag}" || usage failed to create ${MountPointTag}


# build an image in the stage directory
BuildRootFileSystem
if [ X"${ReplaceKernel}" = X"YES" ]
then
  GetTheKernel
fi

# fix some things
ApplyFixes

# create an archive of the stage directory
rm -f "${RootFSArchive}"
RBLD --tar="${RootFSArchive}"

# install to SD Card
if [ X"${InstallToSDCard}" = X"YES" ]
then
  if [ X"${format}" = X"YES" ]
  then
    InstallQi format
  else
    InstallQi no-format
  fi
  InstallRootFileSystem
fi

# finished
UnmountSDCard
