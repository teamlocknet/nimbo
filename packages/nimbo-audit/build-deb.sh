#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
cd "$REPO"
imagen=$(sed -n 's/^DIGEST_DEFAULT="\(.*\)"$/\1/p' \
  packages/nimbo-audit/test-in-bookworm.sh)
test -n "$imagen"
. iso/live-build/snapshot.env

salida=$(mktemp -d /tmp/nimbo-deb-build.XXXXXX)
echo "Artefactos: $salida"

docker run --rm \
  -v "$PWD/packages/nimbo-audit:/src:ro" \
  -v "$salida:/out" \
  -e NIMBO_SNAPSHOT="$NIMBO_SNAPSHOT" \
  -e HOST_UID="${SUDO_UID:-$(id -u)}" \
  -e HOST_GID="${SUDO_GID:-$(id -g)}" \
  -e DEBIAN_FRONTEND=noninteractive \
  -e TZ=UTC \
  -e LC_ALL=C.UTF-8 \
  "$imagen" bash -euo pipefail -c '
    printf "deb http://snapshot.debian.org/archive/debian/%s/ bookworm main\n" \
      "$NIMBO_SNAPSHOT" > /etc/apt/sources.list
    rm -f /etc/apt/sources.list.d/debian.sources
    printf "Acquire::Check-Valid-Until \"false\";\nAcquire::Retries \"5\";\n" \
      > /etc/apt/apt.conf.d/99nimbo-snapshot
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends \
      build-essential fakeroot debhelper dh-python \
      pybuild-plugin-pyproject python3-all python3-setuptools \
      python3-pytest python3-typer > /tmp/apt-install.log 2>&1 \
      || { cat /tmp/apt-install.log; exit 1; }

    mkdir -p /build
    cp -a /src /build/nimbo-audit
    cd /build/nimbo-audit
    dpkg-buildpackage -us -uc -b
    cp /build/*.deb /build/*.buildinfo /build/*.changes /out/
    chown "$HOST_UID:$HOST_GID" /out/*
    dpkg-deb -f /out/nimbo-audit_0.1.0-1_all.deb \
      Package Version Architecture Depends Suggests
    sha256sum /out/*.deb
  ' 2>&1 | tee "$salida/build.log"
