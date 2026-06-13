.PHONY: setup start stop test lint type-check backend-check web-check

PIXI ?= $(shell command -v pixi 2>/dev/null || python3 -c 'from pathlib import Path; print(Path.home() / ".pixi/bin/pixi")')

setup:
	$(PIXI) install
	cd web/app && npm ci --ignore-scripts

start:
	$(PIXI) run dev-all

stop:
	$(PIXI) run dev-down

test:
	$(PIXI) run test

lint:
	$(PIXI) run lint-ruff
	cd web/app && PATH="./node_modules/.bin:$$PATH" npm run lint

type-check:
	$(PIXI) run type-check
	cd web/app && PATH="./node_modules/.bin:$$PATH" npm run type-check

backend-check:
	$(PIXI) run lint-ruff
	$(PIXI) run type-check
	$(PIXI) run test

web-check:
	cd web/app && PATH="./node_modules/.bin:$$PATH" npm run lint
	cd web/app && PATH="./node_modules/.bin:$$PATH" npm run type-check
	cd web/app && PATH="./node_modules/.bin:$$PATH" npm run test
	cd web/app && PATH="./node_modules/.bin:$$PATH" npm run build
