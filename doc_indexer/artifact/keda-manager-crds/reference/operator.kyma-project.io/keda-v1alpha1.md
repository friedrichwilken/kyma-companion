# Keda (operator.kyma-project.io/v1alpha1)

Keda is the Schema for the kedas API

Scope: Namespaced · Plural: kedas · Short names:  · Served: yes · Storage: yes

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec.env[].name` | string | yes |  | Name of the environment variable. May consist of any printable ASCII characters except '='. |
| `spec.env[].value` | string | no |  | Variable references $(VAR_NAME) are expanded using the previously defined environment variables in the container and any service environment variables. If a variable cannot be resolved, the reference in the input string will be unchanged. Double $$ are reduced to a single $, which allows for escaping the $(VAR_NAME) syntax: i.e. "$$(VAR_NAME)" will produce the string literal "$(VAR_NAME)". Escaped references will never be expanded, regardless of whether the variable exists or not. Defaults to "". |
| `spec.env[].valueFrom.configMapKeyRef.key` | string | yes |  | The key to select. |
| `spec.env[].valueFrom.configMapKeyRef.name` | string | no |  | Name of the referent. This field is effectively required, but due to backwards compatibility is allowed to be empty. Instances of this type with an empty value here are almost certainly wrong. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names |
| `spec.env[].valueFrom.configMapKeyRef.optional` | boolean | no |  | Specify whether the ConfigMap or its key must be defined |
| `spec.env[].valueFrom.fieldRef.apiVersion` | string | no |  | Version of the schema the FieldPath is written in terms of, defaults to "v1". |
| `spec.env[].valueFrom.fieldRef.fieldPath` | string | yes |  | Path of the field to select in the specified API version. |
| `spec.env[].valueFrom.fileKeyRef.key` | string | yes |  | The key within the env file. An invalid key will prevent the pod from starting. The keys defined within a source may consist of any printable ASCII characters except '='. During Alpha stage of the EnvFiles feature gate, the key size is limited to 128 characters. |
| `spec.env[].valueFrom.fileKeyRef.optional` | boolean | no |  | Specify whether the file or its key must be defined. If the file or key does not exist, then the env var is not published. If optional is set to true and the specified key does not exist, the environment variable will not be set in the Pod's containers. If optional is set to false and the specified key does not exist, an error will be returned during Pod creation. |
| `spec.env[].valueFrom.fileKeyRef.path` | string | yes |  | The path within the volume from which to select the file. Must be relative and may not contain the '..' path or start with '..'. |
| `spec.env[].valueFrom.fileKeyRef.volumeName` | string | yes |  | The name of the volume mount containing the env file. |
| `spec.env[].valueFrom.resourceFieldRef.containerName` | string | no |  | Container name: required for volumes, optional for env vars |
| `spec.env[].valueFrom.resourceFieldRef.divisor` |  | no |  | Specifies the output format of the exposed resources, defaults to "1" |
| `spec.env[].valueFrom.resourceFieldRef.resource` | string | yes |  | Required: resource to select |
| `spec.env[].valueFrom.secretKeyRef.key` | string | yes |  | The key of the secret to select from. Must be a valid secret key. |
| `spec.env[].valueFrom.secretKeyRef.name` | string | no |  | Name of the referent. This field is effectively required, but due to backwards compatibility is allowed to be empty. Instances of this type with an empty value here are almost certainly wrong. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names |
| `spec.env[].valueFrom.secretKeyRef.optional` | boolean | no |  | Specify whether the Secret or its key must be defined |
| `spec.istio.metricServer.enabledSidecarInjection` | boolean | no |  |  |
| `spec.istio.operator.enabledSidecarInjection` | boolean | no |  |  |
| `spec.logging.admissionWebhook.format` | string | no | `json`, `text`, `console` |  |
| `spec.logging.admissionWebhook.level` | string | no | `debug`, `info`, `error` |  |
| `spec.logging.admissionWebhook.timeEncoding` | string | no | `epoch`, `millis`, `nano`, `iso8601`, `rfc3339`, `rfc3339nano` |  |
| `spec.logging.metricServer.format` | string | no | `json`, `text`, `console` |  |
| `spec.logging.metricServer.level` | string | no | `debug`, `info`, `error` |  |
| `spec.logging.metricServer.timeEncoding` | string | no | `epoch`, `millis`, `nano`, `iso8601`, `rfc3339`, `rfc3339nano` |  |
| `spec.logging.operator.format` | string | no | `json`, `text`, `console` |  |
| `spec.logging.operator.level` | string | no | `debug`, `info`, `error` |  |
| `spec.logging.operator.timeEncoding` | string | no | `epoch`, `millis`, `nano`, `iso8601`, `rfc3339`, `rfc3339nano` |  |
| `spec.podAnnotations.admissionWebhook.*` | string | no |  |  |
| `spec.podAnnotations.metricServer.*` | string | no |  |  |
| `spec.podAnnotations.operator.*` | string | no |  |  |
| `spec.resources.admissionWebhook.claims[].name` | string | yes |  | Name must match the name of one entry in pod.spec.resourceClaims of the Pod where this field is used. It makes that resource available inside a container. |
| `spec.resources.admissionWebhook.claims[].request` | string | no |  | Request is the name chosen for a request in the referenced claim. If empty, everything from the claim is made available, otherwise only the result of this request. |
| `spec.resources.admissionWebhook.limits.*` |  | no |  |  |
| `spec.resources.admissionWebhook.requests.*` |  | no |  |  |
| `spec.resources.metricServer.claims[].name` | string | yes |  | Name must match the name of one entry in pod.spec.resourceClaims of the Pod where this field is used. It makes that resource available inside a container. |
| `spec.resources.metricServer.claims[].request` | string | no |  | Request is the name chosen for a request in the referenced claim. If empty, everything from the claim is made available, otherwise only the result of this request. |
| `spec.resources.metricServer.limits.*` |  | no |  |  |
| `spec.resources.metricServer.requests.*` |  | no |  |  |
| `spec.resources.operator.claims[].name` | string | yes |  | Name must match the name of one entry in pod.spec.resourceClaims of the Pod where this field is used. It makes that resource available inside a container. |
| `spec.resources.operator.claims[].request` | string | no |  | Request is the name chosen for a request in the referenced claim. If empty, everything from the claim is made available, otherwise only the result of this request. |
| `spec.resources.operator.limits.*` |  | no |  |  |
| `spec.resources.operator.requests.*` |  | no |  |  |

## Status

| Field | Type | Values | Description |
|---|---|---|---|
| `kedaVersion` | string |  |  |
| `served` | string |  |  |
| `state` | string |  |  |
