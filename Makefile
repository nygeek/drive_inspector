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
	drivefile.py \
	drivefilecached.py \
	drivefileraw.py \
	drivereport.py \
	driveshell.py

SOURCE = \
	${PYTHON_SOURCE} \
	Makefile \
	README.md

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
	pylint ${PYTHON_SOURCE}

lint: pylint

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
	rsync -az --exclude=".git*" --exclude=".*_push" -e ssh ${DIRS} $*:${DIRPATH}
	touch $@

FORCE: 
