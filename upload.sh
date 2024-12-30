#!/bin/bash
set -e -x

export name=faddnsc
export pkgname=${name}
export pkgrel=1

test -f package.zip

if [ "$1" == "" ]; then
  export datetime=`gawk "BEGIN {print strftime(\"%Y%m%d%H%M%S\")}"`
  echo "devel version $datetime"
  #export branch=`git rev-parse --abbrev-ref HEAD`
  #export pkgname=${pkgname}.dev.${branch}
  export pkgname=${pkgname}.dev
  export version=$datetime
  #export upload=atxpkg@atxpkg-dev.asterix.cz:atxpkg/
  export upload=scp://atxpkg@atxpkg-dev.asterix.cz:2224/atxpkg/
elif [ "$1" == "release" ]; then
  export version=`git describe --tags --abbrev=0`
  export version=${version:1}
  echo "release version $version"
  #export upload=atxpkg@atxpkg.asterix.cz:atxpkg/
  export upload=scp://atxpkg@atxpkg.asterix.cz:2225/atxpkg/
else
  echo "unknown parameter!"
  exit
fi

#export sshopts='-i ./id_rsa_atxpkg -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
export sshopts='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

export pkg_fn=${pkgname}-${version}-${pkgrel}.atxpkg.zip

mv package.zip $pkg_fn

#rsync -avP $pkg_fn $upload
scp -B ${sshopts} ${pkg_fn} ${upload}

echo "DONE: ${pkg_fn}"
