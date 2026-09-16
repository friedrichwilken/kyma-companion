# BtpOperator (operator.kyma-project.io/v1alpha1)

BtpOperator is the Schema for the btpoperators API

Scope: Namespaced · Plural: btpoperators · Short names:  · Served: yes · Storage: yes

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec` | object | no |  | BtpOperatorSpec defines the desired state of BtpOperator |

## Status

| Field | Type | Values | Description |
|---|---|---|---|
| `state` | string | `Processing`, `Deleting`, `Ready`, `Error`, `Warning` | State signifies current state of CustomObject. Value can be one of ("Ready", "Processing", "Error", "Deleting", "Warning"). |
