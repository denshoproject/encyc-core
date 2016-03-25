SHELL = /bin/bash

PROJECT=encyc-cmdln
APP=encyc
USER=encyc

INSTALL_BASE=/usr/local/src
INSTALLDIR=$(INSTALL_BASE)/encyc-cmdln
DOWNLOADS_DIR=/tmp/$(APP)-install
PIP_CACHE_DIR=$(INSTALL_BASE)/pip-cache
VIRTUALENV=$(INSTALL_BASE)/env/$(APP)

LOGS_BASE=/var/log/$(PROJECT)

.PHONY: help


help:
	@echo "encyc-rg Install Helper"
	@echo ""
	@echo "get     - Downloads source, installers, and assets files. Does not install."
	@echo ""
	@echo "install - Installs app, config files, and static assets.  Does not download."
	@echo ""
	@echo "update  - Updates encyc-rg and re-copies config files."
	@echo ""
	@echo "reload  - Reloads supervisord and nginx configs"
	@echo ""
	@echo "uninstall - Deletes 'compiled' Python files. Leaves build dirs and configs."
	@echo "clean   - Deletes files created by building the program. Leaves configs."
	@echo ""
	@echo "branch BRANCH=[branch] - Switches encyc-rg and supporting repos to [branch]."
	@echo ""


get: get-app apt-update

install: install-prep install-app install-configs

update: update-app

uninstall: uninstall-app

clean: clean-app


install-prep: apt-upgrade install-core git-config install-misc-tools

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
	pip install -U --download-cache=$(PIP_CACHE_DIR) bpython setuptools


get-app: get-encyc-cmdln

install-app: install-encyc-cmdln

update-app: update-encyc-cmdln install-configs

uninstall-app: uninstall-encyc-cmdln

clean-app: clean-encyc-cmdln


get-encyc-cmdln:
	git pull
	pip install --download=$(PIP_CACHE_DIR) --exists-action=i -r $(INSTALLDIR)/encyc/requirements/production.txt

install-encyc-cmdln: install-virtualenv
	@echo ""
	@echo "install encyc-cmdln -----------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	pip install -U --no-index --find-links=$(PIP_CACHE_DIR) -r $(INSTALLDIR)/encyc/requirements/production.txt
# logs dir
	-mkdir $(LOGS_BASE)
	chown -R $(USER).root $(LOGS_BASE)
	chmod -R 755 $(LOGS_BASE)

update-encyc-cmdln:
	@echo ""
	@echo "update encyc-rg ---------------------------------------------------------"
	git fetch && git pull
	source $(VIRTUALENV)/bin/activate; \
	pip install -U --no-download --download-cache=$(PIP_CACHE_DIR) -r $(INSTALLDIR)/encyc/requirements/production.txt

uninstall-encyc-cmdln:
	@echo ""
	@echo "uninstall encyc-rg ------------------------------------------------------"
	cd $(INSTALLDIR)/encyc-cmdln
	source $(VIRTUALENV)/bin/activate; \
	-pip uninstall -r $(INSTALLDIR)/encyc/requirements/production.txt
	-rm /usr/local/lib/python2.7/dist-packages/encyc-*
	-rm -Rf /usr/local/lib/python2.7/dist-packages/encyc

clean-encyc-cmdln:
	-rm -Rf $(INSTALLDIR)/encyc/src

clean-pip:
	-rm -Rf $(PIP_CACHE_DIR)/*


branch:
	cd $(INSTALLDIR)/encyc; python ./bin/git-checkout-branch.py $(BRANCH)


install-configs:
	@echo ""
	@echo "install configs ---------------------------------------------------------"
	cp $(INSTALLDIR)/conf/settings.py $(DJANGO_CONF)
	chown root.root $(DJANGO_CONF)
	chmod 644 $(DJANGO_CONF)

uninstall-configs:
	-rm $(DJANGO_CONF)
	-rm $(CONFIG_KEY)
	-rm $(CONFIG_PROD)
