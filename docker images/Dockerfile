FROM ubuntu:20.04
# used p4lang/p4app before, but contained switch does not support thrift currently, maybe take a look at 2.0.0 as soon as it is released

# basic install depedencies
RUN DEBIAN_FRONTEND=noninteractive apt-get -y update
RUN DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends --fix-missing install \
  sudo \
  curl \
  git \
  ca-certificates \
  openssh-server \
  openjdk-11-jdk


COPY libglib2.0-0_2.64.6-1~ubuntu20.04.7_amd64.deb /tmp/
RUN dpkg -i /tmp/libglib2.0-0_2.64.6-1~ubuntu20.04.7_amd64.deb



RUN sudo apt-get install -y openjdk-11-jdk

# add a user p4 with password p4 as used by common p4 tutorials
RUN sudo useradd -m -d /home/p4 -s /bin/bash p4
RUN echo "p4:p4" | chpasswd
RUN echo "p4 ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
RUN sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config
USER p4
WORKDIR /home/p4

# install packages needed for common assignments
RUN sudo DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends --fix-missing install \
  tmux \
  iperf \
  iperf3 \
  net-tools \
  iputils-tracepath \
  iputils-ping \
  # mtr \
  htop \
  tcpdump \
  # tshark \
  wget \
  unzip \
  vim \
  joe \
  nano \
  patch \
  lsb-release

# install node
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
RUN sudo DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends --fix-missing install\
  nodejs
RUN git clone https://github.com/jafingerhut/p4-guide
RUN p4-guide/bin/install-p4dev-v5.sh
RUN sudo pip3 install pyyaml
RUN sudo pip3 install influxdb
RUN sudo pip3 install confluent_kafka
RUN git clone https://github.com/p4lang/tutorials
# cleanup
RUN sudo DEBIAN_FRONTEND=noninteractive apt-get -y clean
RUN wget https://dl.influxdata.com/influxdb/releases/influxdb_1.8.10_amd64.deb
RUN sudo dpkg -i influxdb_1.8.10_amd64.deb
RUN mkdir pot
WORKDIR /home/p4/pot