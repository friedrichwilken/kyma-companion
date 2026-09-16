"""Unit tests for the resource kind to module mapping."""

import pytest

from docs.modules import module_for_kind


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("APIRule", "api-gateway"),
        ("apirule", "api-gateway"),
        ("Function", "serverless"),
        ("Subscription", "eventing-manager"),
        ("LogPipeline", "telemetry-manager"),
        ("ServiceBinding", "btp-manager"),
        ("VirtualService", "istio"),
        ("Kyma", "kyma"),
        ("Deployment", ""),
        ("", ""),
    ],
)
def test_module_for_kind(kind: str, expected: str) -> None:
    assert module_for_kind(kind) == expected
