"""Compatibility shim -- re-exports types from :mod:`curation.types`.

All curation modules should import from :mod:`curation.types` directly.
This module exists only to satisfy imports in code generated before
``types.py`` was introduced as the canonical location.
"""

from curation.types import CandidateDoc, ClassificationResult, CuratorConfig

__all__ = ["CandidateDoc", "ClassificationResult", "CuratorConfig"]
