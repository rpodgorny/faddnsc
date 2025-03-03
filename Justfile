# some "classic" ways to cross-compile (fast but packaging to deb throws some errors because i'm not on debian?)

deb-raspi1:
  env CROSS_CONTAINER_ENGINE=podman /home/radek/.cargo/bin/cross build --release --target=arm-unknown-linux-gnueabihf
  cargo deb --target=arm-unknown-linux-gnueabihf --no-build

deb-arm64:
  cargo deb --target=aarch64-unknown-linux-gnu

deb:
  cargo deb

deb-all: deb-raspi1 deb-arm64 deb

push-all-deb: deb-all
  scp target/debian/*.deb target/*-linux-*/debian/*.deb scp://deb@deb.asterix.cz:2212/debs/bookworm/

# following are podman-based builds (the best but slow?)

build-debian codename:
  podman run -it --rm --arch=amd64 -v .:/x docker.io/library/rust:{{codename}} /bin/sh -c "cargo install cargo-deb; cd /x; cargo deb -o target/deb/{{codename}}/"
  podman run -it --rm --arch=arm64/v8 -v .:/x docker.io/library/rust:{{codename}} /bin/sh -c "cargo install cargo-deb; cd /x; cargo deb -o target/deb/{{codename}}/"
  podman run -it --rm --arch=arm/v7 -v .:/x docker.io/library/rust:{{codename}} /bin/sh -c "cargo install cargo-deb; cd /x; cargo deb -o target/deb/{{codename}}/"

build-debian-all: (build-debian "bullseye") (build-debian "bookworm")

build-ubuntu codename:
  podman run -it --rm --arch=amd64 -v .:/x docker.io/library/ubuntu:{{codename}} /bin/sh -c "apt update && apt install cargo -y; cargo install cargo-deb; cd /x; cargo deb -o target/deb/{{codename}}/"
  podman run -it --rm --arch=arm64/v8 -v .:/x docker.io/library/ubuntu:{{codename}} /bin/sh -c "apt update && apt install cargo -y; cargo install cargo-deb; cd /x; cargo deb -o target/deb/{{codename}}/"
  podman run -it --rm --arch=arm/v7 -v .:/x docker.io/library/ubuntu:{{codename}} /bin/sh -c "apt update && apt install cargo -y; cargo install cargo-deb; cd /x; cargo deb -o target/deb/{{codename}}/"

build-ubuntu-all: (build-ubuntu "focal") (build-ubuntu "jammy") (build-ubuntu "noble")

push-debian-ubuntu: build-debian-all build-ubuntu-all
  scp -r target/deb/* scp://deb@deb.asterix.cz:2212/debs/
