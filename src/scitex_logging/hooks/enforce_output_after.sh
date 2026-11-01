#!/bin/sh
# Post-tool binding shares the leaf-owned detector with pre-tool and audit.
exec python3 -m scitex_logging._output._hook
