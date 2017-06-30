SHELL = /bin/bash

PROJECT=encyc-core
APP=encyc
USER=encyc

INSTALL_BASE=/usr/local/src
INSTALLDIR=$(INSTALL_BASE)/encyc-core
DOWNLOADS_DIR=/tmp/$(APP)-install
PIP_REQUIREMENTS_DIR=$(INSTALLDIR)/requirements
PIP_CACHE_DIR=$(INSTALL_BASE)/pip-cache
VIRTUALENV=$(INSTALLDIR)/env

LOGS_BASE=/var/log/$(PROJECT)

.PHONY: help


help:
	@echo "encyc-core Install Helper"
	@echo ""
	@echo "get     - Downloads source, installers, and assets files. Does not install."
	@echo ""
	@echo "install - Installs app, config files, and static assets.  Does not download."
	@echo ""
	@echo "update  - Updates encyc-core and re-copies config files."
	@echo ""
	@echo "uninstall - Deletes 'compiled' Python files. Leaves build dirs and configs."
	@echo "clean   - Deletes files created by building the program. Leaves configs."
	@echo ""
	@echo "branch BRANCH=[branch] - Switches encyc-core and supporting repos to [branch]."
	@echo ""


get: get-app apt-update

install: install-prep install-app install-configs

update: update-app

uninstall: uninstall-app

clean: clean-app


install-prep: apt-upgrade install-core git-config install-misc-tools install-setuptools

apt-update:
	@echo ""
	@echo "Package update ---------------------------------------------------------"
	apt-get --assume-yes update

apt-upgrade:
	@echo ""
	@echo "Package upgrade --------------------------------------------------------"
	apt-get --assume-yes upgrade

install-core:
	apt-get --assume-yes install bzip2 curl gdebi-core logrotate ntp p7zip-full wget

git-config:
	git config --global alias.st status
	git config --global alias.co checkout
	git config --global alias.br branch
	git config --global alias.ci commit

install-misc-tools:
	@echo ""
	@echo "Installing miscellaneous tools -----------------------------------------"
	apt-get --assume-yes install ack-grep byobu elinks htop mg multitail

install-virtualenv:
	apt-get --assume-yes install python-pip python-virtualenv
	test -d $(VIRTUALENV) || virtualenv --distribute --setuptools $(VIRTUALENV)

install-setuptools: install-virtualenv
	@echo ""
	@echo "install-setuptools -----------------------------------------------------"
	apt-get --assume-yes install python-dev
	source $(VIRTUALENV)/bin/activate; \
	pip install -U --download-cache=$(PIP_CACHE_DIR) setuptools


get-app: get-encyc-core

install-app: install-setuptools install-encyc-core

update-app: update-encyc-core install-configs

uninstall-app: uninstall-encyc-core

clean-app: clean-encyc-core


get-dev:
	source $(VIRTUALENV)/bin/activate; \
	pip install --download=$(PIP_CACHE_DIR) --exists-action=i -r $(PIP_REQUIREMENTS_DIR)/dev.txt

install-dev:
	source $(VIRTUALENV)/bin/activate; \
	pip install -U --find-links=$(PIP_CACHE_DIR) -r $(PIP_REQUIREMENTS_DIR)/dev.txt


get-encyc-core:
	git pull
	source $(VIRTUALENV)/bin/activate; \
	pip install --download=$(PIP_CACHE_DIR) --exists-action=i -r $(PIP_REQUIREMENTS_DIR)/production.txt

setup-encyc-core: install-configs
	@echo ""
	@echo "setup encyc-core -----------------------------------------------------"
	cd $(INSTALLDIR)
	source $(VIRTUALENV)/bin/activate; \
	python setup.py install
# logs dir
	-mkdir $(LOGS_BASE)
	chown -R $(USER).root $(LOGS_BASE)
	chmod -R 755 $(LOGS_BASE)

install-encyc-core:
	@echo ""
	@echo "install encyc-core -----------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	pip install -U --find-links=$(PIP_CACHE_DIR) -r $(PIP_REQUIREMENTS_DIR)/production.txt
	cd $(INSTALLDIR)
	source $(VIRTUALENV)/bin/activate; \
	python setup.py install
# logs dir
	-mkdir $(LOGS_BASE)
	chown -R $(USER).root $(LOGS_BASE)
	chmod -R 755 $(LOGS_BASE)

update-encyc-core:
	@echo ""
	@echo "update encyc-core ---------------------------------------------------------"
	git fetch && git pull
	source $(VIRTUALENV)/bin/activate; \
	pip install -U --no-download --download-cache=$(PIP_CACHE_DIR) -r $(PIP_REQUIREMENTS_DIR)/production.txt

uninstall-encyc-core:
	@echo ""
	@echo "uninstall encyc-core ------------------------------------------------------"
	cd $(INSTALLDIR)/encyc-core
	source $(VIRTUALENV)/bin/activate; \
	-pip uninstall -r $(PIP_REQUIREMENTS_DIR)/production.txt
	-rm /usr/local/lib/python2.7/dist-packages/encyc-*
	-rm -Rf /usr/local/lib/python2.7/dist-packages/encyc

clean-encyc-core:
	-rm     $(INSTALLDIR)/encyc/*.pyc
	-rm -Rf $(INSTALLDIR)/encyc_core.egg-info/
	-rm -Rf $(INSTALLDIR)/build/
	-rm -Rf $(INSTALLDIR)/dist/
	-rm -Rf $(VIRTUALENV)/lib/python2.7/site-packages/encyc*
	-rm     $(VIRTUALENV)/bin/encyc
	-rm -Rf /usr/local/lib/python2.7/dist-packages/encyc*

clean-pip:
	-rm -Rf $(PIP_CACHE_DIR)/*


branch:
	cd $(INSTALLDIR)/encyc; python ./bin/git-checkout-branch.py $(BRANCH)


install-configs:
	@echo ""
	@echo "install configs ---------------------------------------------------------"
	-mkdir /etc/encyc
	cp $(INSTALLDIR)/conf/core.cfg /etc/encyc/
	chown root.encyc /etc/encyc/core.cfg
	chmod 640 /etc/encyc/core.cfg
	touch /etc/encyc/core-local.cfg
	chown root.encyc /etc/encyc/core-local.cfg
	chmod 640 /etc/encyc/core-local.cfg

uninstall-configs:
