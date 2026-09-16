# Subscription (eventing.kyma-project.io/v1alpha2)

Subscription is the Schema for the subscriptions API.

Scope: Namespaced · Plural: subscriptions · Short names:  · Served: yes · Storage: yes

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec.config.*` | string | no |  |  |
| `spec.id` | string | no |  | Unique identifier of the Subscription, read-only. |
| `spec.sink` | string | yes |  | Kubernetes Service that should be used as a target for the events that match the Subscription. Must exist in the same Namespace as the Subscription. |
| `spec.source` | string | yes |  | Defines the origin of the event. |
| `spec.typeMatching` | string | no |  | Defines how types should be handled.<br /> - `standard`: backend-specific logic will be applied to the configured source and types.<br /> - `exact`: no further processing will be applied to the configured source and types. |
| `spec.types[]` | string | yes |  |  |

## Status

| Field | Type | Values | Description |
|---|---|---|---|
| `backend.apiRuleName` | string |  | Name of the APIRule which is used by the Subscription. |
| `backend.emsSubscriptionStatus.lastFailedDelivery` | string |  | Timestamp of the last failed delivery. |
| `backend.emsSubscriptionStatus.lastFailedDeliveryReason` | string |  | Reason for the last failed delivery. |
| `backend.emsSubscriptionStatus.lastSuccessfulDelivery` | string |  | Timestamp of the last successful delivery. |
| `backend.emsSubscriptionStatus.status` | string |  | Status of the Subscription as reported by the backend. |
| `backend.emsSubscriptionStatus.statusReason` | string |  | Reason for the current status. |
| `backend.emsTypes[].eventMeshType` | string |  | Event type that is used on the EventMesh backend. |
| `backend.emsTypes[].originalType` | string |  | Event type that was originally used to subscribe. |
| `backend.emshash` | integer |  | Hash used to identify an EventMesh Subscription retrieved from the server without the WebhookAuth config. |
| `backend.ev2hash` | integer |  | Checksum for the Subscription custom resource. |
| `backend.eventMeshLocalHash` | integer |  | Hash used to identify an EventMesh Subscription posted to the server without the WebhookAuth config. |
| `backend.externalSink` | string |  | Webhook URL used by EventMesh to trigger subscribers. |
| `backend.failedActivation` | string |  | Provides the reason if a Subscription failed activation in EventMesh. |
| `backend.types[].consumerName` | string |  | Name of the JetStream consumer created for the event type. |
| `backend.types[].originalType` | string |  | Event type that was originally used to subscribe. |
| `backend.webhookAuthHash` | integer |  | Hash used to identify the WebhookAuth of an EventMesh Subscription existing on the server. |
| `ready` | boolean |  | Overall readiness of the Subscription. |
| `types[].cleanType` | string |  | Event type after it was cleaned up from backend compatible characters. |
| `types[].originalType` | string |  | Event type as specified in the Subscription spec. |
