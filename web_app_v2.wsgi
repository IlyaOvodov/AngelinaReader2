#!/usr/bin/python
import sys
import logging
from pathlib import Path
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,str(Path(__file__).parent))
from web_app_v2 import app as application
