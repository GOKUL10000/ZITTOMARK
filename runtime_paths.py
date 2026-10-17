"""Portable runtime location; no machine-specific username or installation path."""
import os
from pathlib import Path

APP = Path(__file__).resolve().parent
default = Path(os.environ['LOCALAPPDATA'])/'Zittomark'/'runtime' if os.environ.get('LOCALAPPDATA') else APP/'.runtime'
RUNTIME = Path(os.environ.get('OVS_RUNTIME_ROOT',str(default))).expanduser().resolve()
os.environ.setdefault('HF_HOME',str(RUNTIME/'hf-cache'))
