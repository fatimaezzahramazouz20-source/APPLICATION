# -*- coding: utf-8 -*-
"""Vérifie que app.py s'exécute sans exception (y compris le dashboard)."""
import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))

from streamlit.testing.v1 import AppTest  # noqa: E402

at = AppTest.from_file(os.path.join(os.path.dirname(BASE), "app.py"),
                       default_timeout=120)
at.session_state["use_sample"] = True
at.run()

errs = list(at.exception)
print(f"Exceptions : {len(errs)}")
for e in errs:
    print(" -", e.value if hasattr(e, "value") else e)

metrics = [m.label for m in at.metric]
print(f"KPIs affichés : {metrics}")
print("OK" if not errs else "ECHEC")
