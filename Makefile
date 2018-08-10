#
# drive-inspector Makefile
#

# Two flavors:
# Linux
# DATE := $(shell date --rfc-3339=seconds)
#
# MacOS
DATE := $(shell date "+%Y-%m-%d")

DIRS = "."
DIRPATH="~/projects/d/drive-inspector/src"

BUILD_VERSION := $(shell cat version.txt)

HOSTS = waffle pancake
PUSH_FILES = $(HOSTS:%=.%_push)

help: ${FORCE}
	echo ${DATE}
	cat Makefile

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

clean: ${FORCE}
	-rm ${CACHE} *.pyc

# support data
FILES = \
	${SOURCE} \
	pylintrc \
	.gitattributes \
	.gitignore

tar: drive_inspector.tar

drive_inspector.tar: ${FORCE}
	tar -cvf $@ ${FILES}

# Quality management

pylint: ${FORCE}
	- pylint drivefileraw.py
	- pylint drivefilecached.py
	- pylint driveshell.py
	- pylint drivereport.py

lint: pylint

test: test-cached

test-raw: ${FORCE}
	python drivefileraw.py --help
	# this is "Marc Donner Engineering Workbook"
	python drivefileraw.py --stat 1LhX7Z2ffUxPFoLYwNT8lguumohzgwscygX0Tlv4_oYs
	# this is "/people/d"
	python drivefileraw.py --ls 0B_mGZa1CyME_dlRLZnJSdFM4ZDA
	python drivefileraw.py --find 0B_mGZa1CyME_dlRLZnJSdFM4ZDA

test-cached: ${FORCE}
	python drivefilecached.py --help
	python drivefilecached.py --stat '/workbooks/Marc Donner Engineering Workbook'
	python drivefilecached.py --ls /people/d
	python drivefilecached.py --find /people/d

rebuild-cache: ${FORCE}
	- rm ${CACHE}
	python drivefilecached.py --showall -o ${DATE}-showall-cold.txt
	grep '^#' ${DATE}-showall-cold.txt

hide_credentials: ${FORCE}
	mv ~/.credentials/credentials.json ~/tmp

restore_credentials: ${FORCE}
	mv ~/tmp/credentials.json ~/.credentials

check_credentials: ${FORCE}
	ls -l ~/.credentials/{.client_secret.json,credentials.json}

inventory: ${FORCE}
	python drivereport.py 
	mv dr_output.tsv ${DATE}-drive-inventory.tsv

# GIT operations

diff: .gitattributes
	git diff

status: ${FORCE}
	git status

# this brings the remote copy into sync with the local one
commit: .gitattributes
	git commit ${FILES}
	git push -u origin master
	git describe --abbrev=4 --dirty --always --tags > version.txt

# This brings the local copy into sync with the remote (master)
pull: .gitattributes
	git pull origin master

version.txt: ${FORCE}
	git describe --abbrev=4 --dirty --always --tags > version.txt

log: .gitattributes version.txt
	git log --pretty=oneline

# Distribution to other hosts

push: ${PUSH_FILES}
	rm ${PUSH_FILES}

.%_push:
	# rsync -az --exclude=".git*" --exclude=".*_push" -e ssh ${DIRS} $*:${DIRPATH}
	rsync -az --exclude runs --exclude=".*_push" -e ssh ${DIRS} $*:${DIRPATH}
	touch $@

FORCE: 
