$setup = <<SCRIPT
set -x
sudo DEBIAN_FRONTEND=noninteractive apt-get -y update
sudo DEBIAN_FRONTEND=noninteractive apt-get -y dist-upgrade curl git parallel pigz tshark \
    npm python3-pip python3-virtualenv python3-dev \
    libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev \
    libncurses5-dev libreadline6-dev libsqlite3-dev libssl-dev \
    lzma lzma-dev tk-dev uuid-dev zlib1g-dev libmpdec-dev \
    cm-super dvipng texlive-fonts-extra texlive-latex-extra texlive-pictures
yes | sudo DEBIAN_FRONTEND=teletype dpkg-reconfigure wireshark-common
sudo usermod -a -G wireshark ${USER}
set +x

su - vagrant -c "\
set -x; \
/home/vagrant/cbor-dns-eval-tbd/pyenv-setup.sh
echo 'pyenv activate cbor-dns-eval-tbd' >> /home/vagrant/.bashrc; \
( \
  cd /home/vagrant/cbor-dns-eval-tbd/03_json2cbor_eval/; \
  npm install  @sourcemeta/json-taxonomy \
); \
set +x"

set -x
export NAME=jupyter

# Create service file
# TBD needs to be fixed once repo is published
cat >/etc/systemd/system/${NAME}.service <<EOF
[Unit]
Description=${NAME}

[Service]
Type=simple
ExecStart=bash -c "source /home/vagrant/.pyenv/versions/cbor-dns-eval-tbd/bin/activate; /home/vagrant/.pyenv/versions/cbor-dns-eval-tbd/bin/jupyter lab --ip 0.0.0.0 --LabApp.token=''"

WorkingDirectory=/home/vagrant/cbor-dns-eval-tbd
User=vagrant
Group=vagrant

Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl enable --now ${NAME}

set +x
SCRIPT

Vagrant.configure("2") do |config|
  config.vm.define "cbor-dns-eval-tbd"
  config.vm.box = "generic/ubuntu2204"
  config.vm.network "forwarded_port", guest: 8888, host: 8888
  config.vm.synced_folder ".", "/home/vagrant/cbor-dns-eval-tbd", create: true, group: "vagrant", owner: "vagrant"
  config.vm.provision "shell", inline: $setup

  config.ssh.forward_agent = true
  config.ssh.connect_timeout = 90

  config.vm.provider "virtualbox" do |v|
    v.memory = 8192
    v.cpus = 8
  end
end
