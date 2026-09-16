# APIRule (gateway.kyma-project.io/v2alpha1)

APIRule is the Schema for ApiRule APIs.

Scope: Namespaced · Plural: apirules · Short names:  · Served: yes · Storage: yes

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec.corsPolicy.allowCredentials` | boolean | no |  |  |
| `spec.corsPolicy.allowHeaders[]` | string | no |  |  |
| `spec.corsPolicy.allowMethods[]` | string | no |  |  |
| `spec.corsPolicy.allowOrigins[].*` | string | no |  |  |
| `spec.corsPolicy.exposeHeaders[]` | string | no |  |  |
| `spec.corsPolicy.maxAge` | integer | no |  |  |
| `spec.externalGateway` | string | no |  | Specifies the ExternalGateway. The field must reference an existing ExternalGateway in the cluster. Provide the ExternalGateway in the format `namespace/externalgatewayname`. Mutually exclusive with Gateway. |
| `spec.gateway` | string | no |  | Specifies the Istio Gateway to be used. Mutually exclusive with ExternalGateway. |
| `spec.hosts[]` | string | yes |  | Host is the URL of the exposed service. We support lowercase RFC 1123 labels and FQDN. |
| `spec.rules[].extAuth.authorizers[]` | string | yes |  |  |
| `spec.rules[].extAuth.restrictions.authentications[].fromHeaders[].name` | string | yes |  |  |
| `spec.rules[].extAuth.restrictions.authentications[].fromHeaders[].prefix` | string | no |  |  |
| `spec.rules[].extAuth.restrictions.authentications[].fromParams[]` | string | no |  |  |
| `spec.rules[].extAuth.restrictions.authentications[].issuer` | string | yes |  |  |
| `spec.rules[].extAuth.restrictions.authentications[].jwksUri` | string | yes |  |  |
| `spec.rules[].extAuth.restrictions.authorizations[].audiences[]` | string | no |  |  |
| `spec.rules[].extAuth.restrictions.authorizations[].requiredScopes[]` | string | no |  |  |
| `spec.rules[].jwt.authentications[].fromHeaders[].name` | string | yes |  |  |
| `spec.rules[].jwt.authentications[].fromHeaders[].prefix` | string | no |  |  |
| `spec.rules[].jwt.authentications[].fromParams[]` | string | no |  |  |
| `spec.rules[].jwt.authentications[].issuer` | string | yes |  |  |
| `spec.rules[].jwt.authentications[].jwksUri` | string | yes |  |  |
| `spec.rules[].jwt.authorizations[].audiences[]` | string | no |  |  |
| `spec.rules[].jwt.authorizations[].requiredScopes[]` | string | no |  |  |
| `spec.rules[].methods[]` | string | yes | `GET`, `HEAD`, `POST`, `PUT`, `DELETE`, `CONNECT`, `OPTIONS`, `TRACE`, `PATCH` | HttpMethod specifies the HTTP request method. The list of supported methods is defined in RFC 9910: HTTP Semantics and RFC 5789: PATCH Method for HTTP. |
| `spec.rules[].noAuth` | boolean | no |  | Disables authorization when set to true. |
| `spec.rules[].path` | string | yes |  | Specifies the path on which the service is exposed. Supported configurations are: - Exact path (e.g. /abc) - matches the specified path exactly. - Usage of the `{*}` operator (e.g. `/foo/{*}` or `/foo/{*}/bar`) - match any request that matches the pattern with exactly one path segment in the operator's place. - Usage of the `{**}` operator (e.g. `/foo/{**}` or `/foo/{**}/bar`) - match any request that matches the pattern with zero or more path segments in the operator's place. The `{**}` operator must be the last operator in the path. - Wildcard path `/*` - matches all paths. Equivalent to `/{**}` path. |
| `spec.rules[].request.cookies.*` | string | no |  |  |
| `spec.rules[].request.headers.*` | string | no |  |  |
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
| `description` | string |  | Description of APIRule status |
| `lastProcessedTime` | string |  |  |
| `state` | string | `Processing`, `Deleting`, `Ready`, `Error`, `Warning` | State signifies current state of APIRule. Value can be one of ("Ready", "Processing", "Error", "Deleting", "Warning"). |
