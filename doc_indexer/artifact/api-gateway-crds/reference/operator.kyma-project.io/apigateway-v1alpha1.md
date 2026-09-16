# APIGateway (operator.kyma-project.io/v1alpha1)

APIGateway is the Schema for APIGateway APIs.

Scope: Cluster · Plural: apigateways · Short names:  · Served: yes · Storage: yes

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec.enableKymaGateway` | boolean | no |  | Specifies whether the default Kyma Gateway `kyma-gateway` in `kyma-system` namespace is created. |
| `spec.networkPoliciesEnabled` | boolean | no |  | Enables network policy reconciliation support for the API Gateway module. |

## Status

| Field | Type | Values | Description |
|---|---|---|---|
| `description` | string |  | Contains the description of the APIGateway's state. |
| `state` | string | `Processing`, `Deleting`, `Ready`, `Error`, `Warning` | State signifies current state of APIGateway. The possible values are `Ready`, `Processing`, `Error`, `Deleting`, `Warning`. |
