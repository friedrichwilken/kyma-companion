# RateLimit (gateway.kyma-project.io/v1alpha1)

RateLimit is the Schema for reate limits API.

Scope: Namespaced · Plural: ratelimits · Short names:  · Served: yes · Storage: yes

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec.enableResponseHeaders` | boolean | no |  | Enables **x-rate-limit** response headers. The default value is `false`. |
| `spec.enforce` | boolean | no |  | Controls whether rate limiting is enforced. If true, requests exceeding limits are rejected. If false, request limits are monitored but requests that exceed limits are not blocked. The default value is `true`. |
| `spec.local.buckets[].bucket.fillInterval` | string | yes |  | Specifies the fill interval. During each fill interval, the number of tokens specified in the **tokensPerFill** field is added to the bucket. The bucket cannot contain more than maxTokens tokens. The fillInterval must be greater than or equal to 50ms to avoid excessive refills. |
| `spec.local.buckets[].bucket.maxTokens` | integer | yes |  | The maximum number of tokens that the bucket can hold. This is also the number of tokens that the bucket initially contains. |
| `spec.local.buckets[].bucket.tokensPerFill` | integer | yes |  | The number of tokens added to the bucket during each fill interval. |
| `spec.local.buckets[].headers.*` | string | no |  |  |
| `spec.local.buckets[].path` | string | no |  | Specifies the path for which rate limiting is applied. The path must start with `/`. For example, `/foo`. |
| `spec.local.defaultBucket.fillInterval` | string | yes |  | Specifies the fill interval. During each fill interval, the number of tokens specified in the **tokensPerFill** field is added to the bucket. The bucket cannot contain more than maxTokens tokens. The fillInterval must be greater than or equal to 50ms to avoid excessive refills. |
| `spec.local.defaultBucket.maxTokens` | integer | yes |  | The maximum number of tokens that the bucket can hold. This is also the number of tokens that the bucket initially contains. |
| `spec.local.defaultBucket.tokensPerFill` | integer | yes |  | The number of tokens added to the bucket during each fill interval. |
| `spec.selectorLabels.*` | string | no |  |  |

## Status

| Field | Type | Values | Description |
|---|---|---|---|
| `description` | string |  | Description defines the description of current State of RateLimit. |
| `state` | string |  | State describes the overall status of RateLimit. The possible values are `Ready`, `Warning`, and `Error`. |
