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
# the Python environment is in venv based here.
PYTHON := ./bin/python3
PYLINT := ./bin/pylint

DIRS = "."
DIRPATH="~/projects/d/drive-inspector/src"

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
.PHONY: test_raw

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
	- ${PYLINT} drivefileraw.py
	- ${PYLINT} drivefilecached.py
	- ${PYLINT} driveshell.py
	- ${PYLINT} drivereport.py

lint: pylint

test: test-cached

test-raw:
	${PYTHON} drivefileraw.py --help
	# this is "Engineering Workbook"
	${PYTHON} drivefileraw.py --stat 1LhX7Z2ffUxPFoLYwNT8lguumohzgwscygX0Tlv4_oYs
	# this is "/people/d"
	${PYTHON} drivefileraw.py --ls 0B_mGZa1CyME_dlRLZnJSdFM4ZDA
	${PYTHON} drivefileraw.py --find 0B_mGZa1CyME_dlRLZnJSdFM4ZDA

test-cached:
	${PYTHON} drivefilecached.py --help
	${PYTHON} drivefilecached.py --stat '/workbooks/Engineering Workbook'
	${PYTHON} drivefilecached.py --ls /people/d
	${PYTHON} drivefilecached.py --find /people/d

rebuild:
	- rm ${CACHE}
	${PYTHON} drivefilecached.py --showall -o ${DATE}-showall-cold.txt
	grep '^#' ${DATE}-showall-cold.txt

hide_credentials:
	mv ~/.credentials/credentials.json ~/tmp

restore_credentials:
	mv ~/tmp/credentials.json ~/.credentials

check_credentials:
	ls -l ~/.credentials/{.client_secret.json,credentials.json}

inventory:
	${PYTHON} drivereport.py 
	mv dr_output.tsv ${DATE}-drive-inventory.tsv

# GIT operations

diff: .gitattributes
	git diff

status:
	git status

# this brings the remote copy into sync with the local one
commit: .gitattributes
	git commit ${FILES}
	git push -u --tags origin master 

# This brings the local copy into sync with the remote (master)
pull: .gitattributes
	git pull origin master

log: .gitattributes
	git log --pretty=oneline
