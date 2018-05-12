#
# drive-inventory
#

DIRS = "."
DIRPATH="~/projects/d/drive-inventory"

BUILD_VERSION := $(shell cat version.txt)

HOSTS = waffle pancake
PUSH_FILES = $(HOSTS:%=.%_push)

help: ${FORCE}
	cat Makefile

SOURCE = \
	drivefile.py \
	driveshell.py \
	Makefile \
	README.md

# 
DATAFILES = 

CACHE = filedata-cache.json

clean: ${FORCE}
	rm ${CACHE}

# support data
FILES = \
	${SOURCE} \
	pylintrc \
	.gitignore

stuff.tar: ${FORCE}
	tar -cvf stuff.tar ${FILES}

# Need to think about this ... the data to parse is not static
# and I don't really want to stash it all in the data subdir.

# DATA = data/panix.com.ping.log
DATA = 

CRUNCHER = 

test: ${FORCE}
	head -100000 ${DATA} > ${HOME}/tmp/test.txt
	python ${CRUNCHER} -v ${BUILD_VERSION} -f ${HOME}/tmp/test.txt

run: ${FORCE}
	python ${CRUNCHER} -v ${BUILD_VERSION} -f ${DATA}

# Quality management

pylint: ${FORCE}
	pylint drivefile.py

lint: ${FORCE}
	pylint drivefile.py

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
