.PHONY: check test integrity smoke

check:
	python scripts/verify_integrity.py
	python scripts/smoke_ui.py
	python -m pytest tests

test:
	python -m pytest tests

integrity:
	python scripts/verify_integrity.py

smoke:
	python scripts/smoke_ui.py
