#!/bin/sh
# Render start command for stochastiq-dashboard.
set -e

exec streamlit run dashboard/Home.py --server.address 0.0.0.0 --server.port "$PORT" --server.headless true
