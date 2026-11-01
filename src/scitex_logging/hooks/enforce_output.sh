#!/bin/sh
# The Python package owns the implementation; this binding ships in its wheel.
exec python3 -m scitex_logging._output._hook
