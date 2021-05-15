#
# drive-inspector Makefile
#

# Make us OS-independent ... at least for MacOS and Linux
OS := $(shell uname -s)
ifeq (Linux, ${OS})
	DATE := $(shell date --iso-8601)
else
	DATE := $(shell date "+%Y-%m-%d")
endif

# Python version
PYTHON := python3
# PYTHON := python2

DIRS = "."
DIRPATH="~/projects/d/drive-inspector/src"

BUILD_VERSION := $(shell cat version.txt)

HOSTS = flapjack
PUSH_FILES = $(HOSTS:%=.%_push)

.PHONY: help
help:
	cat Makefile
	echo "OS: " ${OS}
	echo "DATE: " ${DATE}

PYTHON_SOURCE = \
	drivefile.py \
	drivefilecached.py \
	drivefileraw.py \
	drivereport.py \
	driveshell.py

SOURCE = \
	${PYTHON_SOURCE} \
	code-of-conduct.md \
	LICENSE \
	Makefile \
	README.md \
	ROADMAP.md

# 
DATAFILES = 

CACHE = .filedata-cache.json

.PHONY: check_credentials clean drive_inspector.tar hide_credentials
.PHONY: inventory pylint rebuild restore_credentials status test-cached
.PHONY: test_raw version.txt

clean:
	-rm ${CACHE} *.pyc

# Examples from documentation

.PHONY: example1 example2 example3

example1:
	${PYTHON} drivefilecached.py --ls /

example2:
	${PYTHON} drivefilecached.py --stat /

example3:
	${PYTHON} drivefilecached.py --find /

example4:
	${PYTHON} drivefilecached.py -f --find root

# support data
FILES = \
	${SOURCE} \
	pylintrc \
	.gitattributes \
	.gitignore

tar: drive_inspector.tar

drive_inspector.tar:
	tar -cvf $@ ${FILES}

# Quality management

pylint:
	- pylint drivefileraw.py
	- pylint drivefilecached.py
	- pylint driveshell.py
	- pylint drivereport.py

lint: pylint

test: test-cached

test_raw:
	python3 drivefileraw.py --help
	# this is "Marc Donner Engineering Workbook"
	python3 drivefileraw.py --stat 1LhX7Z2ffUxPFoLYwNT8lguumohzgwscygX0Tlv4_oYs
	# this is "/people/d"
	python3 drivefileraw.py --ls 0B_mGZa1CyME_dlRLZnJSdFM4ZDA
	python3 drivefileraw.py --find 0B_mGZa1CyME_dlRLZnJSdFM4ZDA

test-cached:
	python3 drivefilecached.py --help
	python3 drivefilecached.py --stat '/workbooks/Marc Donner Engineering Workbook'
	python3 drivefilecached.py --ls /people/d
	python3 drivefilecached.py --find /people/d

rebuild:
	- rm ${CACHE}
	python3 drivefilecached.py --showall -o ${DATE}-showall-cold.txt
	grep '^#' ${DATE}-showall-cold.txt

hide_credentials:
	mv ~/.credentials/credentials.json ~/tmp

restore_credentials:
	mv ~/tmp/credentials.json ~/.credentials

check_credentials:
	ls -l ~/.credentials/{.client_secret.json,credentials.json}

inventory:
	python3 drivereport.py 
	mv dr_output.tsv ${DATE}-drive-inventory.tsv

# GIT operations

diff: .gitattributes
	git diff

status:
	git status

# this brings the remote copy into sync with the local one
commit: .gitattributes
	git commit ${FILES}
	git push -u origin master
	git push --tags
	git describe --dirty --always --tags > version.txt

# This brings the local copy into sync with the remote (master)
pull: .gitattributes
	git pull origin master

version.txt:
	git describe --dirty --always --tags > version.txt

log: .gitattributes version.txt
	git log --pretty=oneline
