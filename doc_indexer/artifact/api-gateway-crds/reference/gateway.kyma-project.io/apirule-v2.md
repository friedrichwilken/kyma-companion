# APIRule (gateway.kyma-project.io/v2)

APIRule is the schema for APIRule APIs.

Scope: Namespaced · Plural: apirules · Short names:  · Served: yes · Storage: no

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec.corsPolicy.allowCredentials` | boolean | no |  | Lists origins allowed with the **Access-Control-Allow-Origins** CORS header. |
| `spec.corsPolicy.allowHeaders[]` | string | no |  |  |
| `spec.corsPolicy.allowMethods[]` | string | no |  |  |
| `spec.corsPolicy.allowOrigins[].*` | string | no |  |  |
| `spec.corsPolicy.exposeHeaders[]` | string | no |  |  |
| `spec.corsPolicy.maxAge` | integer | no |  | Specifies the maximum age of CORS policy cache. The value is provided in the **Access-Control-Max-Age** CORS header. |
| `spec.externalGateway` | string | no |  | Specifies the ExternalGateway. The field must reference an existing ExternalGateway in the cluster. Provide the ExternalGateway in the format `namespace/externalgatewayname`. Both the namespace and the ExternalGateway name cannot be longer than 63 characters each. Mutually exclusive with Gateway. |
| `spec.gateway` | string | no |  | Specifies the Istio Gateway. The field must reference an existing Gateway in the cluster. Provide the Gateway in the format `namespace/gateway`. Both the namespace and the Gateway name cannot be longer than 63 characters each. Mutually exclusive with ExternalGateway. |
| `spec.hosts[]` | string | yes |  | The host is the URL of the exposed Service. Lowercase RFC 1123 labels, FQDN, and wildcard domain names (for example, `*.example.com`) are supported. |
| `spec.rules[].extAuth.authorizers[]` | string | yes |  |  |
| `spec.rules[].extAuth.restrictions.authentications[].fromHeaders[].name` | string | yes |  | Specifies the name of the header from which the JWT token is extracted. |
| `spec.rules[].extAuth.restrictions.authentications[].fromHeaders[].prefix` | string | no |  | Specifies the prefix used before the JWT token. The default is `Bearer`. |
| `spec.rules[].extAuth.restrictions.authentications[].fromParams[]` | string | no |  |  |
| `spec.rules[].extAuth.restrictions.authentications[].issuer` | string | yes |  | Identifies the issuer that issued the JWT. The value must be a URL. Although HTTP is allowed, it is recommended that you use only HTTPS endpoints. |
| `spec.rules[].extAuth.restrictions.authentications[].jwksUri` | string | yes |  | Contains the URL of the provider’s public key set to validate the signature of the JWT. The value must be a URL. Although HTTP is allowed, it is recommended that you use only HTTPS endpoints. |
| `spec.rules[].extAuth.restrictions.authorizations[].audiences[]` | string | no |  |  |
| `spec.rules[].extAuth.restrictions.authorizations[].requiredScopes[]` | string | no |  |  |
| `spec.rules[].jwt.authentications[].fromHeaders[].name` | string | yes |  | Specifies the name of the header from which the JWT token is extracted. |
| `spec.rules[].jwt.authentications[].fromHeaders[].prefix` | string | no |  | Specifies the prefix used before the JWT token. The default is `Bearer`. |
| `spec.rules[].jwt.authentications[].fromParams[]` | string | no |  |  |
| `spec.rules[].jwt.authentications[].issuer` | string | yes |  | Identifies the issuer that issued the JWT. The value must be a URL. Although HTTP is allowed, it is recommended that you use only HTTPS endpoints. |
| `spec.rules[].jwt.authentications[].jwksUri` | string | yes |  | Contains the URL of the provider’s public key set to validate the signature of the JWT. The value must be a URL. Although HTTP is allowed, it is recommended that you use only HTTPS endpoints. |
| `spec.rules[].jwt.authorizations[].audiences[]` | string | no |  |  |
| `spec.rules[].jwt.authorizations[].requiredScopes[]` | string | no |  |  |
| `spec.rules[].methods[]` | string | yes | `GET`, `HEAD`, `POST`, `PUT`, `DELETE`, `CONNECT`, `OPTIONS`, `TRACE`, `PATCH` | HttpMethod specifies the HTTP request method. The list of supported methods is defined in in [RFC 9910: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) and [RFC 5789: PATCH Method for HTTP](https://www.rfc-editor.org/rfc/rfc5789.html). |
| `spec.rules[].noAuth` | boolean | no |  | Disables authorization when set to `true`. |
| `spec.rules[].path` | string | yes |  | Specifies the path on which the Service is exposed. The supported configurations are: - Exact path (e.g. /abc) - matches the specified path exactly. - The `{*}` operator (for example, `/foo/{*}` or `/foo/{*}/bar`) - matches any request that matches the pattern with exactly one path segment in the operator's place. - The `{**}` operator (for example, `/foo/{**}` or `/foo/{**}/bar`) - matches any request that matches the pattern with zero or more path segments in the operator's place. The `{**}` operator must be the last operator in the path. - The wildcard path `/*` - matches all paths. Equivalent to the `/{**}` path. The value might contain the operators `{*}` and/or `{**}`. It can also be a wildcard match `/*`. For more information, see [Ordering Rules in APIRule v2](https://kyma-project.io/external-content/api-gateway/docs/user/expose-workloads/significance-of-rule-path-and-method-order.html). |
| `spec.rules[].request.cookies.*` | string | no |  |  |
| `spec.rules[].request.headers.*` | string | no |  |  |
| `spec.rules[].service.external` | boolean | no |  | Specifies if the Service is internal (deployed in the cluster) or external. |
| `spec.rules[].service.name` | string | yes |  | Specifies the name of the exposed Service. |
| `spec.rules[].service.namespace` | string | no |  | Specifies the namespace of the exposed Service. |
| `spec.rules[].service.port` | integer | yes |  | Specifies the communication port of the exposed Service. |
| `spec.rules[].timeout` | integer | no |  | Specifies the timeout, in seconds, for HTTP requests made to spec.rules.path. Timeout definitions set at this level take precedence over any timeout defined at the spec.timeout level. The maximum timeout is limited to 3900 seconds (65 minutes). |
| `spec.service.external` | boolean | no |  | Specifies if the Service is internal (deployed in the cluster) or external. |
| `spec.service.name` | string | yes |  | Specifies the name of the exposed Service. |
| `spec.service.namespace` | string | no |  | Specifies the namespace of the exposed Service. |
| `spec.service.port` | integer | yes |  | Specifies the communication port of the exposed Service. |
| `spec.timeout` | integer | no |  | Specifies the timeout for HTTP requests in seconds for all rules. You can override the value for each rule. If no timeout is specified, the default timeout of 180 seconds applies. |

## Status

| Field | Type | Values | Description |
|---|---|---|---|
| `description` | string |  | Contains the description of the APIRule's status. |
| `lastProcessedTime` | string |  | Represents the last time the APIRule status was processed. |
| `state` | string | `Processing`, `Deleting`, `Ready`, `Error`, `Warning` | Defines the reconciliation state of the APIRule. The possible states are `Ready`, `Warning`, or `Error`. |
