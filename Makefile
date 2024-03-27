# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

all: lint tests

lint:
	tox -e lint

tests:
	tox -e py3

format:
	tox -e format

SRPY_START_COMMIT ?= origin/master
SRPY_END_COMMIT ?= HEAD

check-commits:
	./check-commits.sh $(SRPY_START_COMMIT)..$(SRPY_END_COMMIT)

.PHONY: lint tests format check-commits
