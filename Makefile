#
# drive-inspector
#

DIRS = "."
DIRPATH="~/projects/d/drive-inspector"

BUILD_VERSION := $(shell cat version.txt)

HOSTS = waffle pancake
PUSH_FILES = $(HOSTS:%=.%_push)

help: ${FORCE}
	cat Makefile

PYTHON_SOURCE = \
	drivefilecached.py \
	drivefileraw.py \
	drivereport.py \
	driveshell.py

SOURCE = \
	${PYTHON_SOURCE} \
	LICENSE \
	Makefile \
	README.md \
	ROADMAP.txt

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
	rsync -az --exclude=".*_push" -e ssh ${DIRS} $*:${DIRPATH}/src
	touch $@

FORCE: 
