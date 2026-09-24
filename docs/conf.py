"""Configure the Sphinx reference generated from the backend's docstrings."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

project = "F1 Backend"
language = "en"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode"]
html_theme = "alabaster"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
autodoc_member_order = "bysource"
autodoc_typehints = "signature"
autoclass_content = "both"
