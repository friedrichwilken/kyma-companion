# Eventing (operator.kyma-project.io/v1alpha1)

Eventing is the Schema for the eventing API.

Scope: Namespaced · Plural: eventings · Short names:  · Served: yes · Storage: yes

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec.annotations.*` | string | no |  |  |
| `spec.backend.config.domain` | string | no |  | Domain defines the cluster public domain used to configure the EventMesh Subscriptions and their corresponding ApiRules. |
| `spec.backend.config.eventMeshSecret` | string | no |  | EventMeshSecret defines the namespaced name of the Kubernetes Secret containing EventMesh credentials. The format of name is "namespace/name". |
| `spec.backend.config.eventTypePrefix` | string | no |  | EventTypePrefix defines the prefix for all event types. |
| `spec.backend.config.natsMaxMsgsPerTopic` | integer | no |  | NATSMaxMsgsPerTopic limits how many messages in the NATS stream to retain per subject. |
| `spec.backend.config.natsStreamMaxSize` |  | no |  | NATSStreamMaxSize defines the maximum storage size for stream data. |
| `spec.backend.config.natsStreamReplicas` | integer | no |  | NATSStreamReplicas defines the number of replicas for the stream. |
| `spec.backend.config.natsStreamStorageType` | string | no |  | NATSStreamStorageType defines the storage type for stream data. |
| `spec.backend.type` | string | yes |  | Type defines which backend to use. The value is either `EventMesh`, or `NATS`. |
| `spec.labels.*` | string | no |  |  |
| `spec.logging.logLevel` | string | no |  | LogLevel defines the log level. |
| `spec.publisher.replicas.max` | integer | no |  | Max defines maximum number of replicas. |
| `spec.publisher.replicas.min` | integer | no |  | Min defines minimum number of replicas. |
| `spec.publisher.resources.claims[].name` | string | yes |  | Name must match the name of one entry in pod.spec.resourceClaims of the Pod where this field is used. It makes that resource available inside a container. |
| `spec.publisher.resources.claims[].request` | string | no |  | Request is the name chosen for a request in the referenced claim. If empty, everything from the claim is made available, otherwise only the result of this request. |
| `spec.publisher.resources.limits.*` |  | no |  |  |
| `spec.publisher.resources.requests.*` |  | no |  |  |

## Status

| Field | Type | Values | Description |
|---|---|---|---|
| `activeBackend` | string |  | ActiveBackend shows the backend currently used by the Eventing module. |
| `publisherService` | string |  | PublisherService is the Kubernetes Service for the Eventing Publisher Proxy. |
| `specHash` | integer |  | BackendConfigHash is a hash of the spec.backend configuration, used internally to detect changes. |
| `state` | string |  | State defines the overall status of the Eventing custom resource. It can be `Ready`, `Processing`, `Error`, or `Warning`. |
