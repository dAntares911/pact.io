FROM jenkins/jenkins:lts-jdk17

USER root

RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    ruby ruby-dev \
    curl docker.io \
    build-essential \
    && gem install pact-mock_service pact_broker-client --no-document \
    && rm -rf /var/lib/apt/lists/*

COPY jenkins-config/plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

COPY jenkins-config/jenkins.yaml /var/jenkins_home/casc_configs/jenkins.yaml

ENV CASC_JENKINS_CONFIG=/var/jenkins_home/casc_configs/jenkins.yaml
ENV JENKINS_OPTS="--httpPort=8080"

USER jenkins
