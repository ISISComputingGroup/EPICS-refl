install:
	@echo Nothing to be done for refl as pure python

clean:
	-del *.pyc *.pyd *.pyo

.DEFAULT:
	@echo Nothing to be done for refl as pure python

.PHONY: test

runtests:
	$(PYTHON3) run_all_tests.py
