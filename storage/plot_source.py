"""Plot source priority: Official_Plot (TMDb/OMDb) > Generated_Plot > embedding_text.

`scripts/enrich_official_plots.py` adds Official_Plot/Plot_Source columns.
All readers use best_plot() so enrichment is opt-in and never breaks deploys.
"""
from typing import Mapping, Any


def best_plot(row: Mapping[str, Any], default: str = "No plot available.") -> str:
    for col in ("Official_Plot", "Generated_Plot", "embedding_text"):
        try:
            v = row.get(col, "")
        except AttributeError:
            v = getattr(row, col, "")
        if v and str(v).strip().lower() not in ("", "nan", "none", "no plot available."):
            return str(v).strip()
    return default
