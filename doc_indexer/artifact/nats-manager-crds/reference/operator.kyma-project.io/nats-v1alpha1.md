# NATS (operator.kyma-project.io/v1alpha1)

NATS is the Schema for the NATS API.

Scope: Namespaced · Plural: nats · Short names:  · Served: yes · Storage: yes

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec.annotations.*` | string | no |  |  |
| `spec.cluster.size` | integer | no |  | Size of a NATS cluster, i.e. number of NATS nodes. |
| `spec.jetStream.fileStorage.size` |  | no |  | Size defines the file storage size. If not set, defaults to 20Gi on alicloud and 1Gi on all other providers. |
| `spec.jetStream.fileStorage.storageClassName` | string | no |  | StorageClassName defines the file storage class name. |
| `spec.jetStream.memStorage.enabled` | boolean | no |  | Enabled allows the enablement of memory storage. |
| `spec.jetStream.memStorage.size` |  | no |  | Size defines the mem. |
| `spec.labels.*` | string | no |  |  |
| `spec.logging.debug` | boolean | no |  | Debug allows debug logging. |
| `spec.logging.trace` | boolean | no |  | Trace allows trace logging. |
| `spec.resources.claims[].name` | string | yes |  | Name must match the name of one entry in pod.spec.resourceClaims of the Pod where this field is used. It makes that resource available inside a container. |
| `spec.resources.claims[].request` | string | no |  | Request is the name chosen for a request in the referenced claim. If empty, everything from the claim is made available, otherwise only the result of this request. |
| `spec.resources.limits.*` |  | no |  |  |
| `spec.resources.requests.*` |  | no |  |  |

## Status

| Field | Type | Values | Description |
|---|---|---|---|
| `availabilityZonesUsed` | integer |  |  |
| `state` | string |  |  |
| `url` | string |  |  |
