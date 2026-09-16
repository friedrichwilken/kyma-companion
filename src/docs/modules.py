"""Mapping from Kubernetes resource kinds to the documentation source that covers them.

The Busola UI sends the kind of the resource the user is looking at. Most
Kyma kinds belong to exactly one module, and each module's documentation is
one source directory in the docs artifact (named after the upstream
repository), so the kind can scope a documentation search to that source.
"""

_KIND_TO_MODULE: dict[str, str] = {
    # serverless
    "function": "serverless",
    "serverless": "serverless",
    # api-gateway
    "apirule": "api-gateway",
    "apigateway": "api-gateway",
    "ratelimit": "api-gateway",
    # istio
    "istio": "istio",
    "virtualservice": "istio",
    "gateway": "istio",
    "destinationrule": "istio",
    "peerauthentication": "istio",
    "authorizationpolicy": "istio",
    "requestauthentication": "istio",
    "serviceentry": "istio",
    "sidecar": "istio",
    "envoyfilter": "istio",
    # eventing
    "subscription": "eventing-manager",
    "eventing": "eventing-manager",
    "nats": "nats-manager",
    # telemetry
    "telemetry": "telemetry-manager",
    "logpipeline": "telemetry-manager",
    "logparser": "telemetry-manager",
    "tracepipeline": "telemetry-manager",
    "metricpipeline": "telemetry-manager",
    # btp operator
    "serviceinstance": "btp-manager",
    "servicebinding": "btp-manager",
    "btpoperator": "btp-manager",
    # application connector
    "application": "application-connector-manager",
    "applicationconnector": "application-connector-manager",
    "compassconnection": "application-connector-manager",
    # keda
    "keda": "keda-manager",
    "scaledobject": "keda-manager",
    "scaledjob": "keda-manager",
    "triggerauthentication": "keda-manager",
    "clustertriggerauthentication": "keda-manager",
    # registries
    "dockerregistry": "docker-registry",
    "registrycache": "registry-cache",
    "registryproxy": "registry-proxy",
    # cloud manager
    "cloudresources": "cloud-manager",
    "iprange": "cloud-manager",
    "nfsvolume": "cloud-manager",
    "awsnfsvolume": "cloud-manager",
    "gcpnfsvolume": "cloud-manager",
    "azurerwxvolume": "cloud-manager",
    "vpcpeering": "cloud-manager",
    "awsvpcpeering": "cloud-manager",
    "gcpvpcpeering": "cloud-manager",
    "azurevpcpeering": "cloud-manager",
    "redisinstance": "cloud-manager",
    "awsredisinstance": "cloud-manager",
    "gcpredisinstance": "cloud-manager",
    "azureredisinstance": "cloud-manager",
    # module lifecycle
    "kyma": "kyma",
    "moduletemplate": "kyma",
    "modulereleasemeta": "kyma",
}


def module_for_kind(kind: str) -> str:
    """Return the documentation source name for a resource kind, or an empty string.

    Args:
        kind: A Kubernetes resource kind such as ``"APIRule"``. Matching is
            case-insensitive.

    Returns:
        The docs source name (for example ``"api-gateway"``), or ``""`` when
        the kind is not a Kyma module resource.
    """
    return _KIND_TO_MODULE.get(kind.strip().lower(), "")
