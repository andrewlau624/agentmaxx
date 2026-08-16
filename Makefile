.PHONY: install test

install:
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
	@mkdir -p "$(HOME)/.agentmaxx"
	@cp -R agentmaxx.py providers skills templates tools \
		"$(HOME)/.agentmaxx/"
	@mkdir -p "$(HOME)/.local/bin"
	@printf '%s\n' \
		'#!/bin/sh' \
		'exec python3 "$$HOME/.agentmaxx/agentmaxx.py" "$$@"' \
		> "$(HOME)/.local/bin/agentmaxx"
	@chmod +x "$(HOME)/.local/bin/agentmaxx"
	@python3 "$(HOME)/.agentmaxx/agentmaxx.py" install
	@echo "agentmaxx installed globally."
	@echo "Run 'agentmaxx init' inside a repo to add the output contract there."

test:
	python3 -m unittest discover -s tools -p "test_*.py"