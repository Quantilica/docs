"""Carrega hooks/registro.py como módulo, para as guardas em tools/."""

import importlib.util
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "registro.py"


def carrega_hook():
    spec = importlib.util.spec_from_file_location("registro_hook", HOOK)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["registro_hook"] = modulo
    spec.loader.exec_module(modulo)
    return modulo
