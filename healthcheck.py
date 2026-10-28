"""Check FreeLLMAPI connection without revealing secrets.

Usage:
    python healthcheck.py
    python healthcheck.py --chat
"""

import os
import sys

# Add agent-core to path
root = os.path.dirname(os.path.abspath(__file__))
agent_core_dir = os.path.join(root, "agent-core")
if agent_core_dir not in sys.path:
    sys.path.insert(0, agent_core_dir)

from app.llm.healthcheck import check, main

if __name__ == "__main__":
    main()
