"""Types for the curation package."""

from typing import Literal

from pydantic import BaseModel


class Candidate(BaseModel):
    """A documentation page candidate for curation."""

    repo: str
    """The repository the candidate belongs to."""

    path: str
    """The file path within the repository."""

    h1: str = ""
    """The first H1 heading of the document, if present."""


class ClassificationResult(BaseModel):
    """The result of classifying a documentation candidate."""

    decision: Literal["include", "exclude", "unsure"]
    """The classification decision."""

    rationale: str
    """The rationale for the decision."""

    candidate: Candidate
    """The candidate that was classified."""
