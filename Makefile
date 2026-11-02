PYTHON ?= python3

.PHONY: demo test unit clean

demo:
	./run.sh

test:
	$(PYTHON) selftest.py

unit:
	$(PYTHON) -m unittest discover -s tests -v

clean:
	find . -type f \( -name '*.vo' -o -name '*.vok' -o -name '*.vos' \
		-o -name '*.glob' -o -name '*.aux' -o -name '*.d' \) -delete
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	rm -rf *.egg-info .pytest_cache .ruff_cache
	rm -f sliced.v sliced_stub.v sliced_min.v broken_sliced.v sliced.dot sliced.mmd
	rm -f batch_sliced_*.v slice_min_*.v
