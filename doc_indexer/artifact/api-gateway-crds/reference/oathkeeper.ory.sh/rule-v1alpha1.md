# Rule (oathkeeper.ory.sh/v1alpha1)

Rule is the Schema for the rules API

Scope: Namespaced · Plural: rules · Short names:  · Served: yes · Storage: yes

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec.authenticators[].config` | object | no | preserves unknown fields | Config configures the handler. Configuration keys vary per handler. |
| `spec.authenticators[].handler` | string | yes |  | Name is the name of a handler |
| `spec.authorizer.config` | object | no | preserves unknown fields | Config configures the handler. Configuration keys vary per handler. |
| `spec.authorizer.handler` | string | yes |  | Name is the name of a handler |
| `spec.configMapName` | string | no |  | ConfigMapName points to the K8s ConfigMap that contains these rules |
| `spec.errors[].config` | object | no | preserves unknown fields | Config configures the handler. Configuration keys vary per handler. |
| `spec.errors[].handler` | string | yes |  | Name is the name of a handler |
| `spec.match.methods[]` | string | yes |  |  |
| `spec.match.url` | string | yes |  | URL is the URL that should be matched. It supports regex templates. |
| `spec.mutators[].config` | object | no | preserves unknown fields | Config configures the handler. Configuration keys vary per handler. |
| `spec.mutators[].handler` | string | yes |  | Name is the name of a handler |
| `spec.upstream.preserveHost` | boolean | no |  | PreserveHost includes the host and port of the url value if set to false. If true, the host and port of the ORY Oathkeeper Proxy will be used instead. |
| `spec.upstream.stripPath` | string | no |  | StripPath replaces the provided path prefix when forwarding the requested URL to the upstream URL. |
| `spec.upstream.url` | string | yes |  | URL defines the target URL for incoming requests |

## Status

| Field | Type | Values | Description |
|---|---|---|---|
| `validation.valid` | boolean |  |  |
| `validation.validationError` | string |  |  |
