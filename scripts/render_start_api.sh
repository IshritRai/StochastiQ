#!/bin/sh
# Render start command for stochastiq-api. A plain script file avoids the
# `sh -c "A && B"` quoting that Render's dockerCommand field does not
# reliably pass through a real shell (it can hand the whole quoted string
# to sh as a single, unparsed command name).
set -e

python scripts/demo_bootstrap.py

exec uvicorn app.api.main:app --host 0.0.0.0 --port "$PORT"
