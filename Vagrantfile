# -*- mode: ruby -*-
# vi: set ft=ruby :

$setup_onionperf = <<SCRIPT
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt install -y build-essential autoconf cmake libglib2.0-dev libigraph0-dev libevent-dev libssl-dev python3 git python3-stem python3-lxml python3-networkx python3-matplotlib python3-numpy python3-scipy
cd ~
git clone https://git.torproject.org/tor.git
cd tor
./autogen.sh
./configure --disable-asciidoc
make
mv src/app/tor /usr/local/bin/
cd ~
git clone https://github.com/shadow/shadow.git
cd shadow/src/plugin/shadow-plugin-tgen
mkdir build
cd build
cmake .. -DSKIP_SHADOW=ON -DCMAKE_MODULE_PATH=`pwd`/../../../../cmake/
make
mv tgen /usr/local/bin/
cd /vagrant
python3 setup.py build
python3 setup.py install
SCRIPT

Vagrant.configure("2") do |config|
  config.vm.box = "debian/stretch64"

  config.vm.define "oniondev" do |oniondev|
    oniondev.vm.provision :shell, :inline => $setup_onionperf
  end

end
