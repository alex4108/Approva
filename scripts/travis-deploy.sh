#!/usr/bin/env bash

# Deploys to GitHub Releases
# Rotates version number
# Modifies github release to include CHANGELOG

set -euo pipefail
set -x

STATE=$1
version=$(cat ${TRAVIS_BUILD_DIR}/VERSION)

fixFilesForMaster() { 
    sed -i "s|build: .|alex4108/approova:${version}|g" docker-compose.yml
    sed -i "0,/RELEASE_VERSION/{s/RELEASE_VERSION/${version}/}" CHANGELOG.md
    git add docker-compose.yml
    git add CHANGELOG.md
    git commit -S -m "(CI) Update version"
    git push origin
}

scrubSecrets() { 
    cd ${TRAVIS_BUILD_DIR}
    git reset --hard
}

freshClone() { 
    OLD_PWD=$(pwd)
    ts=$(date +%s)
    mkdir -p /tmp/
    mkdir -p /tmp/${ts}
    cd /tmp/${ts}
    git clone git@github.com:alex4108/Approova.git
    cd /tmp/${ts}/Approova
}

getReleaseId() { 
    trying="1"
    max_tries="10"
    sleep="2"
    try="1"
    while [[ "${trying}" == "1" ]]; do
        release_id=$(curl -H "Accept: application/vnd.github.v3+json" -u alex4108:${GITHUB_PAT} https://api.github.com/repos/alex4108/Approova/releases | jq -r ".[] | select(.tag_name == \"${version}\").id")
        if [[ "${release_id}" == "null" || "${release_id}" == "" ]]; then
            echo "Failed!"
            echo "Sleeping ${sleep} seconds"
            sleep ${sleep}
            sleep=$((${sleep} * ${sleep}))
            try=$((${try} + 1))
        else
            trying=0
        fi

        if [[ "${try}" == "${max_tries}" ]]; then
            echo "You've failed me for the last time!"
            exit 1
        fi
    done
}

# Configures git for GPG Signing
gitConfig() { 
    gpg --import /tmp/travis.gpg
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    /bin/cp -rf /tmp/id_rsa ~/.ssh/id_rsa
    chmod 400 ~/.ssh/id_rsa
    git config --global user.name "Alex Schittko"
    git config --global user.email "alex4108@live.com"
    git config --global user.signingkey DFF8E003A6969029
    echo -e "Host github.com\n    StrictHostKeyChecking no" > ~/.ssh/config
}

# Bumps the version
bumpVersion() { 
    freshClone
    git checkout develop
    echo -e "# Release RELEASE_VERSION\n\n## Breaking Changes\n\n*\n\n## Bugs\n\n*\n\n## Improvements\n\n*\n""" > CHANGELOG.md
    next_version_minor="$(( $(cat ${TRAVIS_BUILD_DIR}/VERSION | cut -d. -f3) + 1 ))"
    next_version="$(cat ${TRAVIS_BUILD_DIR}/VERSION | cut -d. -f1).$(cat ${TRAVIS_BUILD_DIR}/VERSION | cut -d. -f2).${next_version_minor}"
    echo ${next_version} > VERSION
    git add CHANGELOG.md
    git add VERSION
    git commit -S -m "(CI) Reset for next version"
    git push
}

# Tag the release
# Fix docker compose
if [[ "${STATE}" == "BEFORE" ]]; then 
    gitConfig
    freshClone

    git checkout master
    export TRAVIS_TAG="${version}"
    fixFilesForMaster
    git tag -s ${version} -m "Release ${version}"
    git push origin ${version}

    cd ${TRAVIS_BUILD_DIR}
    git tag ${version} -m "Release ${version}"
    scrubSecrets
    

# Update the release in Github
# bump develop's version
elif [[ "${STATE}" == "AFTER" ]]; then 
    gitConfig
    getReleaseId
    sed -i ':a;N;$!ba;s|\n|\\r\\n|g' ${TRAVIS_BUILD_DIR}/CHANGELOG.md
    curl -X PATCH https://api.github.com/repos/alex4108/Approova/releases/${release_id} -u alex4108:${GITHUB_PAT} -d "{\"tag_name\": \"${version}\", \"name\": \"v${version}\", \"body\": \"$(cat ${TRAVIS_BUILD_DIR}/CHANGELOG.md)\"}"
    curl -X PATCH https://api.github.com/repos/alex4108/Approova/releases/${release_id} -u alex4108:${GITHUB_PAT} -d "{\"draft\": \"false\"}"
    bumpVersion
fi
