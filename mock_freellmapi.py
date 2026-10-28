"""Lightweight mock server for hermetic testing and offline development.

Usage:
    python mock_freellmapi.py --port 31415 --key test-key
"""

import os
import sys

# Ensure agent-core is on path
root = os.path.dirname(os.path.abspath(__file__))
agent_core_dir = os.path.join(root, "agent-core")
if agent_core_dir not in sys.path:
    sys.path.insert(0, agent_core_dir)

from mock_freellmapi import app, set_valid_key, VALID_KEY

if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=31415)
    parser.add_argument("--key", default="test-key")
    args = parser.parse_args()
    set_valid_key(args.key)
    uvicorn.run(app, host="127.0.0.1", port=args.port)
