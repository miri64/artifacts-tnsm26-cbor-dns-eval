$setup = <<SCRIPT
set -x
/home/vagrant/cbor-dns-eval-tbd/ubuntu-setup.sh
set +x

su - vagrant -c "\
set -x; \
/home/vagrant/cbor-dns-eval-tbd/pyenv-setup.sh
echo 'pyenv activate cbor-dns-eval-tbd' >> /home/vagrant/.bashrc; \

/home/vagrant/cbor-dns-eval-tbd/03_json2cbor_eval/node-setup.sh
set +x"

set -x
/home/vagrant/cbor-dns-eval-tbd/jupyter-service-setup.sh
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
