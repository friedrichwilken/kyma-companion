# ExternalGateway (gateway.kyma-project.io/v1alpha1)

ExternalGateway defines the Schema for the ExternalGateway API.

Scope: Namespaced · Plural: externalgateways · Short names:  · Served: yes · Storage: yes

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec.caSecretRef.name` | string | no |  | name is unique within a namespace to reference a secret resource. |
| `spec.caSecretRef.namespace` | string | no |  | namespace defines the space within which the secret name must be unique. |
| `spec.externalDomain` | string | yes |  | ExternalDomain is the customer-facing domain, for example, `api.customer.com` or `*.api.customer.com`. It uses the Istio Gateway host format and can include an optional wildcard prefix, for example, `*.example.com`. |
| `spec.includeExtGatewayClientCert` | boolean | no |  | IncludeExtGatewayClientCert controls whether the ExternalGateway client certificate is included in HTTP headers. By default, this option is disabled, so the client certificate is not included. |
| `spec.internalDomain.kymaSubdomain` | string | yes |  | KymaSubdomain specifies the subdomain prefix, for example, `external-myapp`. The full internal domain follows the pattern `{kymaSubdomain}.{KYMA_DOMAIN}`. |
| `spec.region` | string | yes |  | Region contains a region identifier, for example, `eu10` or `us10`. It must match a region defined in the RegionsConfigMap. |
| `spec.regionsConfigMap` | string | yes |  | RegionsConfigMap specifies the name of the ConfigMap that contains region metadata. The ConfigMap must be in the same namespace as the ExternalGateway. If no key is specified in the ConfigMap, it auto-detects a single key or looks for `regions.yaml`. |

## Status

| Field | Type | Values | Description |
|---|---|---|---|
| `description` | string |  | Description provides details about the ExternalGateway status. |
| `lastProcessedTime` | string |  | LastProcessedTime represents the last time the ExternalGateway status was processed. |
| `observedGeneration` | integer |  | ObservedGeneration reflects the **.metadata.generation** when this status was last updated. |
| `state` | string | `Processing`, `Ready`, `Error` | State defines the reconciliation state of the ExternalGateway. |
