#!/bin/bash
set -e -x

export name=faddnsc
export pkgname=${name}
export pkgrel=1

git submodule update --recursive --init

./compile_podman.sh

rm -rf pkg
mkdir pkg
mkdir -p pkg/${name}
cp -av target/x86_64-pc-windows-gnu/release/*.exe pkg/${name}/

rm -rf target

if [ -d pkg_data ]; then
  cp -rv pkg_data/* pkg/
fi

if [ -f atxpkg_backup ]; then
  cp -av atxpkg_backup pkg/.atxpkg_backup
fi

rm -rf package.zip
cd pkg
zip -r ../package.zip .
cd ..
rm -rf pkg

./upload.sh "$@"
