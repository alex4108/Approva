#!/usr/bin/env bash
mkdir -p /tmp/
openssl aes-256-cbc -K $encrypted_f217180e22ee_key -iv $encrypted_f217180e22ee_iv -in ${TRAVIS_BUILD_DIR}/id_rsa.enc -out /tmp/id_rsa -d
openssl aes-256-cbc -K $encrypted_13a541962f09_key -iv $encrypted_13a541962f09_iv -in ${TRAVIS_BUILD_DIR}/travis.gpg.enc -out /tmp/travis.gpg -d
sudo apt purge --auto-remove qemu-user qemu-user-binfmt binfmt-support
sudo apt install qemu-user
sudo rm -rf /var/lib/apt/lists/*
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) edge"
sudo apt-get update
sudo apt-get -y -o Dpkg::Options::="--force-confnew" install docker-ce
mkdir -vp ~/.docker/cli-plugins/
curl --silent -L "https://github.com/docker/buildx/releases/download/v0.5.1/buildx-v0.5.1.linux-amd64" > ~/.docker/cli-plugins/docker-buildx
chmod a+x ~/.docker/cli-plugins/docker-buildx