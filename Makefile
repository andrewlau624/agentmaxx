.PHONY: install stage test telemetry prune

AGENTMAXX = $(HOME)/.agentmaxx/agentmaxx.py

stage:
	@command -v python3 >/dev/null || { \
		echo "Error: python3 is required"; \
		exit 1; \
	}
	@command -v rg >/dev/null || { \
		echo "Installing ripgrep..."; \
		if command -v brew >/dev/null; then \
			brew install ripgrep; \
		elif command -v apt-get >/dev/null; then \
			sudo apt-get update && sudo apt-get install -y ripgrep; \
		else \
			echo "Error: install ripgrep manually"; \
			exit 1; \
		fi; \
	}
	@rm -rf "$(HOME)/.agentmaxx"
	@mkdir -p "$(HOME)/.agentmaxx"
	@cp -R agentmaxx.py providers skills templates tools integrations mcp \
		"$(HOME)/.agentmaxx/"
	@find "$(HOME)/.agentmaxx" -name __pycache__ -type d -prune -exec rm -rf {} +
	@mkdir -p "$(HOME)/.local/bin"
	@printf '%s\n' \
		'#!/bin/sh' \
		'exec python3 "$$HOME/.agentmaxx/agentmaxx.py" "$$@"' \
		> "$(HOME)/.local/bin/agentmaxx"
	@chmod +x "$(HOME)/.local/bin/agentmaxx"

install: stage
	@python3 "$(AGENTMAXX)" install
	@python3 external/install.py
	@echo "agentmaxx installed globally."
	@echo "Run 'agentmaxx init' inside a repo to add the output contract there."

install-%: stage
	@python3 "$(AGENTMAXX)" install --provider $*

test:
	python3 -m unittest discover -s tools -p "test_*.py"
	python3 -m unittest discover -s evals -p "test_*.py" -t .

telemetry:
	python3 evals/token_telemetry.py

prune:
	python3 external/prune_gstack.py
