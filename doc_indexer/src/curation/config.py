"""Configuration dataclass for the curation pipeline."""

from dataclasses import dataclass


@dataclass
class CuratorConfig:
    """Runtime configuration for the document curator.

    Attributes:
        floor_precision: Minimum acceptable precision (0-1).  The eval-classifier
            exits with code 1 if the measured precision falls below this value.
        floor_recall: Minimum acceptable recall (0-1).  The eval-classifier exits
            with code 1 if the measured recall falls below this value.
    """

    floor_precision: float = 0.85
    floor_recall: float = 0.80
