"""Check FreeLLMAPI connection without revealing secrets.

Usage:
    python healthcheck.py
    python healthcheck.py --chat
"""

import os
import sys

cur_dir = os.path.dirname(os.path.abspath(__file__))
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)

from app.llm.healthcheck import check, main

if __name__ == "__main__":
    main()
