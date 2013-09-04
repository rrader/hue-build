#!/bin/bash

sudo yum -y install ruby rubygems

# Install Vagrant
rpm -ivh http://files.vagrantup.com/packages/7ec0ee1d00a916f80b109a298bab08e391945243/vagrant_1.2.7_x86_64.rpm

# Fix for CentOS
sed -i 's/\/Fedora/\/\[CentOS\|Fedora\]/g' /opt/vagrant/embedded/gems/gems/vagrant-1.2.7/plugins/hosts/fedora/host.rb

# Install VirtualBox
wget -O /etc/yum.repos.d/virtualbox.repo http://download.virtualbox.org/virtualbox/rpm/rhel/virtualbox.repo
yum -y install VirtualBox-4.2
usermod -a -G vboxusers jenkins
