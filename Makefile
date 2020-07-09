# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

all: lint tests

lint:
	tox -e lint

tests:
	tox -e py3-devel

format:
	tox -e format

.PHONY: lint tests format
