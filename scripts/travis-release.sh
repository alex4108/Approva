#!/usr/bin/env bash
set -euo pipefail
set -x

source ${TRAVIS_BUILD_DIR}/common.sh


commit=$(git rev-list -n 1 ${TRAVIS_TAG})

# * Re-tag the container
dockerLogin
docker pull alex4108/approova:${commit}
docker tag alex4108/approova:${commit} alex4108/approova:${TRAVIS_TAG}
docker push alex4108/approova:${TRAVIS_TAG}

# * Deploy to kube (LIVE)
cd ${TRAVIS_BUILD_DIR}/scripts
bash 3-deploy-kube.sh

# * Publish github release
# (handled by travis-release-hooks.sh)