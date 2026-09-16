# APIRule (gateway.kyma-project.io/v1beta1)

APIRule is the Schema for ApiRule APIs.

Scope: Namespaced · Plural: apirules · Short names:  · Served: yes · Storage: no

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec.corsPolicy.allowCredentials` | boolean | no |  |  |
| `spec.corsPolicy.allowHeaders[]` | string | no |  |  |
| `spec.corsPolicy.allowMethods[]` | string | no |  |  |
| `spec.corsPolicy.allowOrigins[].*` | string | no |  |  |
| `spec.corsPolicy.exposeHeaders[]` | string | no |  |  |
| `spec.corsPolicy.maxAge` | string | no |  |  |
| `spec.gateway` | string | yes |  | Specifies the Istio Gateway to be used. |
| `spec.host` | string | yes |  | Specifies the URL of the exposed service. |
| `spec.rules[].accessStrategies[].config` | object | no | preserves unknown fields | Configures the handler. Configuration keys vary per handler. |
| `spec.rules[].accessStrategies[].handler` | string | yes |  | Specifies the name of the handler. |
| `spec.rules[].methods[]` | string | yes | `GET`, `HEAD`, `POST`, `PUT`, `DELETE`, `CONNECT`, `OPTIONS`, `TRACE`, `PATCH` | HttpMethod specifies the HTTP request method. The list of supported methods is defined in RFC 9910: HTTP Semantics and RFC 5789: PATCH Method for HTTP. |
| `spec.rules[].mutators[].config` | object | no | preserves unknown fields | Configures the handler. Configuration keys vary per handler. |
| `spec.rules[].mutators[].handler` | string | yes |  | Specifies the name of the handler. |
| `spec.rules[].path` | string | yes |  | Specifies the path of the exposed service. |
| `spec.rules[].service.external` | boolean | no |  | Specifies if the service is internal (in cluster) or external. |
| `spec.rules[].service.name` | string | yes |  | Specifies the name of the exposed service. |
| `spec.rules[].service.namespace` | string | no |  | Specifies the Namespace of the exposed service. If not defined, it defaults to the APIRule Namespace. |
| `spec.rules[].service.port` | integer | yes |  | Specifies the communication port of the exposed service. |
| `spec.rules[].timeout` | integer | no |  | Timeout for HTTP requests in seconds. The timeout can be configured up to 3900 seconds (65 minutes). |
| `spec.service.external` | boolean | no |  | Specifies if the service is internal (in cluster) or external. |
| `spec.service.name` | string | yes |  | Specifies the name of the exposed service. |
| `spec.service.namespace` | string | no |  | Specifies the Namespace of the exposed service. If not defined, it defaults to the APIRule Namespace. |
| `spec.service.port` | integer | yes |  | Specifies the communication port of the exposed service. |
| `spec.timeout` | integer | no |  | Timeout for HTTP requests in seconds. The timeout can be configured up to 3900 seconds (65 minutes). |

## Status

| Field | Type | Values | Description |
|---|---|---|---|
| `APIRuleStatus.code` | string |  | Status code describing APIRule. |
| `APIRuleStatus.desc` | string |  |  |
| `accessRuleStatus.code` | string |  | Status code describing APIRule. |
| `accessRuleStatus.desc` | string |  |  |
| `authorizationPolicyStatus.code` | string |  | Status code describing APIRule. |
| `authorizationPolicyStatus.desc` | string |  |  |
| `lastProcessedTime` | string |  |  |
| `observedGeneration` | integer |  |  |
| `requestAuthenticationStatus.code` | string |  | Status code describing APIRule. |
| `requestAuthenticationStatus.desc` | string |  |  |
| `virtualServiceStatus.code` | string |  | Status code describing APIRule. |
| `virtualServiceStatus.desc` | string |  |  |
