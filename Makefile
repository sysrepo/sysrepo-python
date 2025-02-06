# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

all: lint tests

lint:
	tox -e lint

tests:
	tox -e py3

format:
	tox -e format

SRPY_COMMIT_RANGE ?= origin/master..

check-commits:
	./check-commits.sh $(SRPY_COMMIT_RANGE)

.PHONY: lint tests format check-commits
