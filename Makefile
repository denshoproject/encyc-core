PROJECT=encyc-core
APP=encyccore
USER=encyc
SHELL = /bin/bash

APP_VERSION := $(shell cat VERSION)
GIT_SOURCE_URL=https://github.com/densho/encyc-core

# current branch name minus dashes or underscores
PACKAGE_BRANCH := $(shell git rev-parse --abbrev-ref HEAD | tr -d _ | tr -d -)
# current commit hash
PACKAGE_COMMIT := $(shell git log -1 --pretty="%h")
# current commit date minus dashes
PACKAGE_TIMESTAMP := $(shell git log -1 --pretty="%ad" --date=short | tr -d -)

PACKAGE_SERVER=ddr.densho.org/static/$(APP)

INSTALL_BASE=/opt
INSTALLDIR=$(INSTALL_BASE)/encyc-core
DOWNLOADS_DIR=/tmp/$(APP)-install
PIP_REQUIREMENTS=$(INSTALLDIR)/requirements.txt
PIP_CACHE_DIR=$(INSTALL_BASE)/pip-cache

VIRTUALENV=$(INSTALLDIR)/venv/encyccore

# Release name e.g. jessie
DEBIAN_CODENAME := $(shell lsb_release -sc)
# Release numbers e.g. 8.10
DEBIAN_RELEASE := $(shell lsb_release -sr)
# Sortable major version tag e.g. deb8
DEBIAN_RELEASE_TAG = deb$(shell lsb_release -sr | cut -c1)

TGZ_BRANCH := $(shell python3 bin/package-branch.py)
TGZ_FILE=$(APP)_$(APP_VERSION)
TGZ_DIR=$(INSTALLDIR)/$(TGZ_FILE)
TGZ_CORE=$(TGZ_DIR)/encyc-core

# Adding '-rcN' to VERSION will name the package "ddrlocal-release"
# instead of "ddrlocal-BRANCH"
DEB_BRANCH := $(shell python3 bin/package-branch.py)
DEB_ARCH=amd64
DEB_NAME_BULLSEYE=$(APP)-$(DEB_BRANCH)
DEB_NAME_BOOKWORM=$(APP)-$(DEB_BRANCH)
DEB_NAME_TRIXIE=$(APP)-$(DEB_BRANCH)
# Application version, separator (~), Debian release tag e.g. deb8
# Release tag used because sortable and follows Debian project usage.
DEB_VERSION_BULLSEYE=$(APP_VERSION)~deb11
DEB_VERSION_BOOKWORM=$(APP_VERSION)~deb12
DEB_VERSION_TRIXIE=$(APP_VERSION)~deb13
DEB_FILE_BULLSEYE=$(DEB_NAME_BULLSEYE)_$(DEB_VERSION_BULLSEYE)_$(DEB_ARCH).deb
DEB_FILE_BOOKWORM=$(DEB_NAME_BOOKWORM)_$(DEB_VERSION_BOOKWORM)_$(DEB_ARCH).deb
DEB_FILE_TRIXIE=$(DEB_NAME_TRIXIE)_$(DEB_VERSION_TRIXIE)_$(DEB_ARCH).deb
DEB_VENDOR=Densho.org
DEB_MAINTAINER=<geoffrey.jost@densho.org>
DEB_DESCRIPTION=Encyclopedia publishing tools
DEB_BASE=opt/encyc-core

CONF_BASE=/etc/encyc

LOGS_BASE=/var/log/$(PROJECT)

.PHONY: help


help:
	@echo "encyc-core Install Helper"
	@echo ""
	@echo "get     - Downloads source, installers, and assets files. Does not install."
	@echo "install - Installs app, config files, and static assets.  Does not download."
	@echo "test    - Run unit tests"
	@echo "uninstall - Deletes 'compiled' Python files. Leaves build dirs and configs."
	@echo "clean   - Deletes files created by building the program. Leaves configs."
	@echo "branch BRANCH=[branch] - Switches encyc-core and supporting repos to [branch]."
	@echo ""


get: get-app apt-update

install: install-prep install-app install-configs

test: test-app
coverage: coverage-app

uninstall: uninstall-app

clean: clean-app


install-prep: apt-upgrade

apt-update:
	@echo ""
	@echo "Package update ---------------------------------------------------------"
	apt-get --assume-yes update

apt-upgrade:
	@echo ""
	@echo "Package upgrade --------------------------------------------------------"
	apt-get --assume-yes upgrade

install-core:
	apt-get --assume-yes install bzip2 curl gdebi-core git-core logrotate ntp p7zip-full python3 wget

git-config:
	git config --global alias.st status
	git config --global alias.co checkout
	git config --global alias.br branch
	git config --global alias.ci commit

install-misc-tools:
	@echo ""
	@echo "Installing tools -------------------------------------------------------"
	apt-get --assume-yes install ack-grep byobu bzip2 curl elinks gdebi-core htop logrotate mg multitail ntp p7zip-full wget

install-virtualenv:
	@echo ""
	@echo "install-virtualenv -----------------------------------------------------"
	apt-get --assume-yes install python3-pip python3-venv
	python3 -m venv $(VIRTUALENV)
	source $(VIRTUALENV)/bin/activate; \
	pip3 install -U --cache-dir=$(PIP_CACHE_DIR) uv


get-app: get-encyc-core

install-app: install-encyc-core

test-app: test-encyc-core
coverage-app: coverage-encyc-core

uninstall-app: uninstall-encyc-core

clean-app: clean-encyc-core


get-encyc-core:
	git pull
	source $(VIRTUALENV)/bin/activate; \
	pip3 install --exists-action=i -r $(PIP_REQUIREMENTS)

setup-encyc-core: install-configs
	@echo ""
	@echo "setup encyc-core -----------------------------------------------------"
	cd $(INSTALLDIR)
	source $(VIRTUALENV)/bin/activate; uv pip install .
# logs dir
	-mkdir $(LOGS_BASE)
	chown -R $(USER):root $(LOGS_BASE)
	chmod -R 755 $(LOGS_BASE)

install-encyc-core: install-virtualenv
	@echo ""
	@echo "install encyc-core -----------------------------------------------------"
# bs4 dependency
	apt-get --assume-yes install libxml2 libxml2-dev libxslt1-dev rsync zlib1g-dev
	cd $(INSTALLDIR)
	source $(VIRTUALENV)/bin/activate; uv pip install .
# logs dir
	-mkdir $(LOGS_BASE)
	chown -R $(USER):root $(LOGS_BASE)
	chmod -R 755 $(LOGS_BASE)

test-encyc-core:
	@echo ""
	@echo "test-encyc-core --------------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALLDIR)/; \
	pytest --disable-warnings --rootdir=$(INSTALLDIR) encyc/tests/

coverage-encyc-core:
	@echo ""
	@echo "coverage-encyc-core ----------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALLDIR)/; \
	pytest --disable-warnings --rootdir=$(INSTALLDIR) --cov-config=.coveragerc --cov-report=html --cov=encyc encyc/tests/

mypy-encyc-core:
	@echo ""
	@echo "mypy-encyc-core --------------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALLDIR)/; mypy encyc/

uninstall-encyc-core:
	@echo ""
	@echo "uninstall encyc-core ------------------------------------------------------"
	cd $(INSTALLDIR)/encyc-core
	source $(VIRTUALENV)/bin/activate; \
	-pip3 uninstall -r $(PIP_REQUIREMENTS)
	-rm /usr/local/lib/python2.7/dist-packages/encyc-*
	-rm -Rf /usr/local/lib/python2.7/dist-packages/encyc

clean-encyc-core:
	-rm     $(INSTALLDIR)/encyc/*.pyc
	-rm -Rf $(INSTALLDIR)/encyc_core.egg-info/
	-rm -Rf $(INSTALLDIR)/build/
	-rm -Rf $(INSTALLDIR)/dist/
	-rm -Rf $(INSTALLDIR)/venv/
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
	chown root:encyc /etc/encyc/core.cfg
	chmod 644 /etc/encyc/core.cfg
	touch /etc/encyc/core-local.cfg
	chown root:encyc /etc/encyc/core-local.cfg
	chmod 640 /etc/encyc/core-local.cfg

uninstall-configs:


tgz-local:
	rm -Rf $(TGZ_DIR)
	git clone $(INSTALLDIR) $(TGZ_CORE)
	cd $(TGZ_CORE); git checkout develop; git checkout master
	tar czf $(TGZ_FILE).tgz $(TGZ_FILE)
	rm -Rf $(TGZ_DIR)

tgz:
	rm -Rf $(TGZ_DIR)
	git clone $(GIT_SOURCE_URL) $(TGZ_CORE)
	cd $(TGZ_CORE); git checkout develop; git checkout master
	tar czf $(TGZ_FILE).tgz $(TGZ_FILE)
	rm -Rf $(TGZ_DIR)


# http://fpm.readthedocs.io/en/latest/
install-fpm:
	@echo "install-fpm ------------------------------------------------------------"
	apt-get install --assume-yes ruby ruby-dev rubygems build-essential
	gem install --no-document fpm

# https://stackoverflow.com/questions/32094205/set-a-custom-install-directory-when-making-a-deb-package-with-fpm
# https://brejoc.com/tag/fpm/
deb: deb-bullseye

deb-bullseye:
	@echo ""
	@echo "FPM packaging (bullseye) -----------------------------------------------"
	-rm -Rf $(DEB_FILE_BULLSEYE)
# Make package
	fpm   \
	--verbose   \
	--input-type dir   \
	--output-type deb   \
	--name $(DEB_NAME_BULLSEYE)   \
	--version $(DEB_VERSION_BULLSEYE)   \
	--package $(DEB_FILE_BULLSEYE)   \
	--url "$(GIT_SOURCE_URL)"   \
	--vendor "$(DEB_VENDOR)"   \
	--maintainer "$(DEB_MAINTAINER)"   \
	--description "$(DEB_DESCRIPTION)"   \
	--chdir $(INSTALLDIR)   \
	--depends "python3"   \
	--depends "rsync"   \
	.git=$(DEB_BASE)   \
	.gitignore=$(DEB_BASE)   \
	bin=$(DEB_BASE)   \
	conf=$(DEB_BASE)   \
	COPYRIGHT=$(DEB_BASE)   \
	encyc=$(DEB_BASE)   \
	INSTALL=$(DEB_BASE)   \
	LICENSE=$(DEB_BASE)   \
	Makefile=$(DEB_BASE)   \
	pyproject.toml=$(DEB_BASE)  \
	README.rst=$(DEB_BASE)   \
	VERSION=$(DEB_BASE)  \
	venv=$(DEB_BASE)   \
	conf/core.cfg=$(CONF_BASE)/core.cfg

deb-bookworm:
	@echo ""
	@echo "FPM packaging (bookworm) -----------------------------------------------"
	-rm -Rf $(DEB_FILE_BOOKWORM)
# Make package
	fpm   \
	--verbose   \
	--input-type dir   \
	--output-type deb   \
	--name $(DEB_NAME_BOOKWORM)   \
	--version $(DEB_VERSION_BOOKWORM)   \
	--package $(DEB_FILE_BOOKWORM)   \
	--url "$(GIT_SOURCE_URL)"   \
	--vendor "$(DEB_VENDOR)"   \
	--maintainer "$(DEB_MAINTAINER)"   \
	--description "$(DEB_DESCRIPTION)"   \
	--chdir $(INSTALLDIR)   \
	--depends "python3"   \
	--depends "rsync"   \
	.git=$(DEB_BASE)   \
	.gitignore=$(DEB_BASE)   \
	bin=$(DEB_BASE)   \
	conf=$(DEB_BASE)   \
	COPYRIGHT=$(DEB_BASE)   \
	encyc=$(DEB_BASE)   \
	INSTALL=$(DEB_BASE)   \
	LICENSE=$(DEB_BASE)   \
	Makefile=$(DEB_BASE)   \
	pyproject.toml=$(DEB_BASE)  \
	README.rst=$(DEB_BASE)   \
	VERSION=$(DEB_BASE)  \
	venv=$(DEB_BASE)   \
	conf/core.cfg=$(CONF_BASE)/core.cfg

deb-trixie:
	@echo ""
	@echo "FPM packaging (trixie) -----------------------------------------------"
	-rm -Rf $(DEB_FILE_TRIXIE)
# Make package
	fpm   \
	--verbose   \
	--input-type dir   \
	--output-type deb   \
	--name $(DEB_NAME_TRIXIE)   \
	--version $(DEB_VERSION_TRIXIE)   \
	--package $(DEB_FILE_TRIXIE)   \
	--url "$(GIT_SOURCE_URL)"   \
	--vendor "$(DEB_VENDOR)"   \
	--maintainer "$(DEB_MAINTAINER)"   \
	--description "$(DEB_DESCRIPTION)"   \
	--chdir $(INSTALLDIR)   \
	--depends "python3"   \
	--depends "rsync"   \
	.git=$(DEB_BASE)   \
	.gitignore=$(DEB_BASE)   \
	bin=$(DEB_BASE)   \
	conf=$(DEB_BASE)   \
	COPYRIGHT=$(DEB_BASE)   \
	encyc=$(DEB_BASE)   \
	INSTALL=$(DEB_BASE)   \
	LICENSE=$(DEB_BASE)   \
	Makefile=$(DEB_BASE)   \
	pyproject.toml=$(DEB_BASE)  \
	README.rst=$(DEB_BASE)   \
	VERSION=$(DEB_BASE)  \
	venv=$(DEB_BASE)   \
	conf/core.cfg=$(CONF_BASE)/core.cfg
