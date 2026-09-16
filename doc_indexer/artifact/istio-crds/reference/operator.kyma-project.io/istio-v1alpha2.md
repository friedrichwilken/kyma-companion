# Istio (operator.kyma-project.io/v1alpha2)

Contains the Istio custom resource's specification and its current status.

Scope: Namespaced · Plural: istios · Short names:  · Served: yes · Storage: yes

## Fields

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `spec.compatibilityMode` | boolean | no |  | Enables the compatibility mode for the Istio installation. |
| `spec.components.cni.k8s.affinity.nodeAffinity.preferredDuringSchedulingIgnoredDuringExecution[].preference.matchExpressions[].key` | string | yes |  | The label key that the selector applies to. |
| `spec.components.cni.k8s.affinity.nodeAffinity.preferredDuringSchedulingIgnoredDuringExecution[].preference.matchExpressions[].operator` | string | yes |  | Represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists, DoesNotExist. Gt, and Lt. |
| `spec.components.cni.k8s.affinity.nodeAffinity.preferredDuringSchedulingIgnoredDuringExecution[].preference.matchExpressions[].values[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.nodeAffinity.preferredDuringSchedulingIgnoredDuringExecution[].preference.matchFields[].key` | string | yes |  | The label key that the selector applies to. |
| `spec.components.cni.k8s.affinity.nodeAffinity.preferredDuringSchedulingIgnoredDuringExecution[].preference.matchFields[].operator` | string | yes |  | Represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists, DoesNotExist. Gt, and Lt. |
| `spec.components.cni.k8s.affinity.nodeAffinity.preferredDuringSchedulingIgnoredDuringExecution[].preference.matchFields[].values[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.nodeAffinity.preferredDuringSchedulingIgnoredDuringExecution[].weight` | integer | yes |  | Weight associated with matching the corresponding nodeSelectorTerm, in the range 1-100. |
| `spec.components.cni.k8s.affinity.nodeAffinity.requiredDuringSchedulingIgnoredDuringExecution.nodeSelectorTerms[].matchExpressions[].key` | string | yes |  | The label key that the selector applies to. |
| `spec.components.cni.k8s.affinity.nodeAffinity.requiredDuringSchedulingIgnoredDuringExecution.nodeSelectorTerms[].matchExpressions[].operator` | string | yes |  | Represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists, DoesNotExist. Gt, and Lt. |
| `spec.components.cni.k8s.affinity.nodeAffinity.requiredDuringSchedulingIgnoredDuringExecution.nodeSelectorTerms[].matchExpressions[].values[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.nodeAffinity.requiredDuringSchedulingIgnoredDuringExecution.nodeSelectorTerms[].matchFields[].key` | string | yes |  | The label key that the selector applies to. |
| `spec.components.cni.k8s.affinity.nodeAffinity.requiredDuringSchedulingIgnoredDuringExecution.nodeSelectorTerms[].matchFields[].operator` | string | yes |  | Represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists, DoesNotExist. Gt, and Lt. |
| `spec.components.cni.k8s.affinity.nodeAffinity.requiredDuringSchedulingIgnoredDuringExecution.nodeSelectorTerms[].matchFields[].values[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.labelSelector.matchExpressions[].key` | string | yes |  | key is the label key that the selector applies to. |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.labelSelector.matchExpressions[].operator` | string | yes |  | operator represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists and DoesNotExist. |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.labelSelector.matchExpressions[].values[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.labelSelector.matchLabels.*` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.matchLabelKeys[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.mismatchLabelKeys[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.namespaceSelector.matchExpressions[].key` | string | yes |  | key is the label key that the selector applies to. |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.namespaceSelector.matchExpressions[].operator` | string | yes |  | operator represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists and DoesNotExist. |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.namespaceSelector.matchExpressions[].values[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.namespaceSelector.matchLabels.*` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.namespaces[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.topologyKey` | string | yes |  | This pod should be co-located (affinity) or not co-located (anti-affinity) with the pods matching the labelSelector in the specified namespaces, where co-located is defined as running on a node whose value of the label with key topologyKey matches that of any node on which any of the selected pods is running. Empty topologyKey is not allowed. |
| `spec.components.cni.k8s.affinity.podAffinity.preferredDuringSchedulingIgnoredDuringExecution[].weight` | integer | yes |  | weight associated with matching the corresponding podAffinityTerm, in the range 1-100. |
| `spec.components.cni.k8s.affinity.podAffinity.requiredDuringSchedulingIgnoredDuringExecution[].labelSelector.matchExpressions[].key` | string | yes |  | key is the label key that the selector applies to. |
| `spec.components.cni.k8s.affinity.podAffinity.requiredDuringSchedulingIgnoredDuringExecution[].labelSelector.matchExpressions[].operator` | string | yes |  | operator represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists and DoesNotExist. |
| `spec.components.cni.k8s.affinity.podAffinity.requiredDuringSchedulingIgnoredDuringExecution[].labelSelector.matchExpressions[].values[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.requiredDuringSchedulingIgnoredDuringExecution[].labelSelector.matchLabels.*` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.requiredDuringSchedulingIgnoredDuringExecution[].matchLabelKeys[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.requiredDuringSchedulingIgnoredDuringExecution[].mismatchLabelKeys[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.requiredDuringSchedulingIgnoredDuringExecution[].namespaceSelector.matchExpressions[].key` | string | yes |  | key is the label key that the selector applies to. |
| `spec.components.cni.k8s.affinity.podAffinity.requiredDuringSchedulingIgnoredDuringExecution[].namespaceSelector.matchExpressions[].operator` | string | yes |  | operator represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists and DoesNotExist. |
| `spec.components.cni.k8s.affinity.podAffinity.requiredDuringSchedulingIgnoredDuringExecution[].namespaceSelector.matchExpressions[].values[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.requiredDuringSchedulingIgnoredDuringExecution[].namespaceSelector.matchLabels.*` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.requiredDuringSchedulingIgnoredDuringExecution[].namespaces[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAffinity.requiredDuringSchedulingIgnoredDuringExecution[].topologyKey` | string | yes |  | This pod should be co-located (affinity) or not co-located (anti-affinity) with the pods matching the labelSelector in the specified namespaces, where co-located is defined as running on a node whose value of the label with key topologyKey matches that of any node on which any of the selected pods is running. Empty topologyKey is not allowed. |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.labelSelector.matchExpressions[].key` | string | yes |  | key is the label key that the selector applies to. |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.labelSelector.matchExpressions[].operator` | string | yes |  | operator represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists and DoesNotExist. |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.labelSelector.matchExpressions[].values[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.labelSelector.matchLabels.*` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.matchLabelKeys[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.mismatchLabelKeys[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.namespaceSelector.matchExpressions[].key` | string | yes |  | key is the label key that the selector applies to. |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.namespaceSelector.matchExpressions[].operator` | string | yes |  | operator represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists and DoesNotExist. |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.namespaceSelector.matchExpressions[].values[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.namespaceSelector.matchLabels.*` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.namespaces[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].podAffinityTerm.topologyKey` | string | yes |  | This pod should be co-located (affinity) or not co-located (anti-affinity) with the pods matching the labelSelector in the specified namespaces, where co-located is defined as running on a node whose value of the label with key topologyKey matches that of any node on which any of the selected pods is running. Empty topologyKey is not allowed. |
| `spec.components.cni.k8s.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[].weight` | integer | yes |  | weight associated with matching the corresponding podAffinityTerm, in the range 1-100. |
| `spec.components.cni.k8s.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[].labelSelector.matchExpressions[].key` | string | yes |  | key is the label key that the selector applies to. |
| `spec.components.cni.k8s.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[].labelSelector.matchExpressions[].operator` | string | yes |  | operator represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists and DoesNotExist. |
| `spec.components.cni.k8s.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[].labelSelector.matchExpressions[].values[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[].labelSelector.matchLabels.*` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[].matchLabelKeys[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[].mismatchLabelKeys[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[].namespaceSelector.matchExpressions[].key` | string | yes |  | key is the label key that the selector applies to. |
| `spec.components.cni.k8s.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[].namespaceSelector.matchExpressions[].operator` | string | yes |  | operator represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists and DoesNotExist. |
| `spec.components.cni.k8s.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[].namespaceSelector.matchExpressions[].values[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[].namespaceSelector.matchLabels.*` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[].namespaces[]` | string | no |  |  |
| `spec.components.cni.k8s.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[].topologyKey` | string | yes |  | This pod should be co-located (affinity) or not co-located (anti-affinity) with the pods matching the labelSelector in the specified namespaces, where co-located is defined as running on a node whose value of the label with key topologyKey matches that of any node on which any of the selected pods is running. Empty topologyKey is not allowed. |
| `spec.components.cni.k8s.resources.limits.cpu` | string | no |  | Specifies CPU resource allocation (requests or limits) |
| `spec.components.cni.k8s.resources.limits.memory` | string | no |  | Specifies memory resource allocation (requests or limits). |
| `spec.components.cni.k8s.resources.requests.cpu` | string | no |  | Specifies CPU resource allocation (requests or limits) |
| `spec.components.cni.k8s.resources.requests.memory` | string | no |  | Specifies memory resource allocation (requests or limits). |
| `spec.components.egressGateway.enabled` | boolean | no |  | Enables or disables Istio Egress Gateway. |
| `spec.components.egressGateway.k8s.hpaSpec.maxReplicas` | integer | no |  | Defines the minimum number of replicas for the HorizontalPodAutoscaler. |
| `spec.components.egressGateway.k8s.hpaSpec.minReplicas` | integer | no |  | Defines the maximum number of replicas for the HorizontalPodAutoscaler. |
| `spec.components.egressGateway.k8s.resources.limits.cpu` | string | no |  | Specifies CPU resource allocation (requests or limits) |
| `spec.components.egressGateway.k8s.resources.limits.memory` | string | no |  | Specifies memory resource allocation (requests or limits). |
| `spec.components.egressGateway.k8s.resources.requests.cpu` | string | no |  | Specifies CPU resource allocation (requests or limits) |
| `spec.components.egressGateway.k8s.resources.requests.memory` | string | no |  | Specifies memory resource allocation (requests or limits). |
| `spec.components.egressGateway.k8s.strategy.rollingUpdate.maxSurge` |  | no |  | Specifies the maximum number of Pods that can be created over the desired number of Pods. See [Max Surge](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#max-surge). |
| `spec.components.egressGateway.k8s.strategy.rollingUpdate.maxUnavailable` |  | no |  | Specifies the maximum number of Pods that can be unavailable during the update process. See [Max Unavailable](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#max-unavailable) |
| `spec.components.ingressGateway.k8s.hpaSpec.maxReplicas` | integer | no |  | Defines the minimum number of replicas for the HorizontalPodAutoscaler. |
| `spec.components.ingressGateway.k8s.hpaSpec.minReplicas` | integer | no |  | Defines the maximum number of replicas for the HorizontalPodAutoscaler. |
| `spec.components.ingressGateway.k8s.resources.limits.cpu` | string | no |  | Specifies CPU resource allocation (requests or limits) |
| `spec.components.ingressGateway.k8s.resources.limits.memory` | string | no |  | Specifies memory resource allocation (requests or limits). |
| `spec.components.ingressGateway.k8s.resources.requests.cpu` | string | no |  | Specifies CPU resource allocation (requests or limits) |
| `spec.components.ingressGateway.k8s.resources.requests.memory` | string | no |  | Specifies memory resource allocation (requests or limits). |
| `spec.components.ingressGateway.k8s.strategy.rollingUpdate.maxSurge` |  | no |  | Specifies the maximum number of Pods that can be created over the desired number of Pods. See [Max Surge](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#max-surge). |
| `spec.components.ingressGateway.k8s.strategy.rollingUpdate.maxUnavailable` |  | no |  | Specifies the maximum number of Pods that can be unavailable during the update process. See [Max Unavailable](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#max-unavailable) |
| `spec.components.pilot.k8s.hpaSpec.maxReplicas` | integer | no |  | Defines the minimum number of replicas for the HorizontalPodAutoscaler. |
| `spec.components.pilot.k8s.hpaSpec.minReplicas` | integer | no |  | Defines the maximum number of replicas for the HorizontalPodAutoscaler. |
| `spec.components.pilot.k8s.resources.limits.cpu` | string | no |  | Specifies CPU resource allocation (requests or limits) |
| `spec.components.pilot.k8s.resources.limits.memory` | string | no |  | Specifies memory resource allocation (requests or limits). |
| `spec.components.pilot.k8s.resources.requests.cpu` | string | no |  | Specifies CPU resource allocation (requests or limits) |
| `spec.components.pilot.k8s.resources.requests.memory` | string | no |  | Specifies memory resource allocation (requests or limits). |
| `spec.components.pilot.k8s.strategy.rollingUpdate.maxSurge` |  | no |  | Specifies the maximum number of Pods that can be created over the desired number of Pods. See [Max Surge](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#max-surge). |
| `spec.components.pilot.k8s.strategy.rollingUpdate.maxUnavailable` |  | no |  | Specifies the maximum number of Pods that can be unavailable during the update process. See [Max Unavailable](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#max-unavailable) |
| `spec.components.proxy.k8s.resources.limits.cpu` | string | no |  | Specifies CPU resource allocation (requests or limits) |
| `spec.components.proxy.k8s.resources.limits.memory` | string | no |  | Specifies memory resource allocation (requests or limits). |
| `spec.components.proxy.k8s.resources.requests.cpu` | string | no |  | Specifies CPU resource allocation (requests or limits) |
| `spec.components.proxy.k8s.resources.requests.memory` | string | no |  | Specifies memory resource allocation (requests or limits). |
| `spec.config.authorizers[].headers.inCheck.add.*` | string | no |  |  |
| `spec.config.authorizers[].headers.inCheck.include[]` | string | no |  |  |
| `spec.config.authorizers[].headers.toDownstream.onAllow[]` | string | no |  |  |
| `spec.config.authorizers[].headers.toDownstream.onDeny[]` | string | no |  |  |
| `spec.config.authorizers[].headers.toUpstream.onAllow[]` | string | no |  |  |
| `spec.config.authorizers[].name` | string | yes |  | Specifies a unique name identifying the authorization provider. |
| `spec.config.authorizers[].pathPrefix` | string | no |  | Specifies the prefix included in the request sent to the authorization service. The prefix might be constructed with special characters (for example, `/test?original_path=`). |
| `spec.config.authorizers[].port` | integer | yes |  | Specifies the port of the Service. |
| `spec.config.authorizers[].service` | string | no |  | Specifies the service that implements the Envoy `ext_authz` HTTP authorization service. The recommended format is `[Namespace/]Hostname`. Specify the namespace if it is required to unambiguously resolve a service in the service registry. The host name refers to the fully qualified host name of a service defined by either a Kubernetes Service or a ServiceEntry. |
| `spec.config.authorizers[].timeout` | string | no |  | Specifies the timeout for the HTTP authorization request to the external service. |
| `spec.config.enableDNSProxying` | boolean | no |  | Enables or disables global DNS proxying in Istio sidecar and gateway proxies across the service mesh. When enabled, DNS requests from application Pods are intercepted by Istio proxies instead of being sent directly to upstream DNS servers. Enabling this setting allows Istio proxies to distinguish traffic between two different TCP services that are outside the mesh thanks to virtual IP address assignment to each ServiceEntry from reserved IP range 240.240.0.0/16. |
| `spec.config.forwardClientCertDetails` | string | no | `APPEND_FORWARD`, `SANITIZE_SET`, `SANITIZE`, `ALWAYS_FORWARD_ONLY`, `FORWARD_ONLY` | Defines the strategy of handling the **X-Forwarded-Client-Cert** header only by the gateway proxies. This setting controls how the gateway proxy retrieves client attributes from incoming traffic and propagates them to upstream services in the cluster. Gateway proxies in Istio module are represented by the Istio Ingress Gateway and Istio Egress Gateway. The default behavior for gateway proxies is "SANITIZE_SET". |
| `spec.config.gatewayExternalTrafficPolicy` | string | no | `Local`, `Cluster` | Defines the external traffic policy for the Istio Ingress Gateway Service. Valid configurations are `"Local"` or `"Cluster"`. The external traffic policy set to `"Local"` preserves the client IP in the request, but also introduces the risk of unbalanced traffic distribution. WARNING: Switching **externalTrafficPolicy** may result in a temporal increase in request delay. Make sure that this is acceptable. |
| `spec.config.numTrustedProxies` | integer | no |  | Defines the number of trusted proxies deployed in front of the Istio gateway proxy. |
| `spec.config.proxyStatsMatcher.inclusionRegexps[]` | string | no |  |  |
| `spec.config.telemetry.metrics.prometheusMerge` | boolean | no |  | Defines whether the **prometheusMerge** feature is enabled. If it is, appropriate prometheus.io annotations are added to all data plane Pods to set up scraping. If these annotations already exist, they are overwritten. With this option, the Envoy sidecar merges Istio’s metrics with the application metrics. The merged metrics are scraped from `:15020/stats/prometheus`. |
| `spec.config.trustDomain` | string | no |  | Defines trust domain configuration of Istio. |
| `spec.experimental.enableAmbient` | boolean | no |  | Enables ambient mode support. |
| `spec.experimental.pilot.enableAlphaGatewayAPI` | boolean | no |  | Defines alpha Gateway API support. |
| `spec.experimental.pilot.enableMultiNetworkDiscoverGatewayAPI` | boolean | no |  | Enables multi-network discovery for Gateway API. |
| `spec.networkPoliciesEnabled` | boolean | no |  | Enables installation of network policies that are required for the module to work under a deny-all traffic policy in the `kyma-system` and `istio-system` namespaces. The default value is `false`, which means that the network policies aren't installed. This enforces a secure-by-default posture in the cluster. Enabling this option is likely to cause connectivity issues in the cluster if you don't properly set up your workloads first. |

## Status

| Field | Type | Values | Description |
|---|---|---|---|
| `description` | string |  | Describes the Istio status. |
| `state` | string | `Processing`, `Deleting`, `Ready`, `Error`, `Warning` | Signifies the current state of the Istio custom resource. Possible values are `Ready`, `Processing`, `Error`, `Deleting`, or `Warning`. |
