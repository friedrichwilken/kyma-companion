<!-- loio33883ddf855f47b1b77c44119b7679c4 -->

# ClusterRole Aggregation in Kyma

Kyma modules use Kubernetes `ClusterRole` aggregation to automatically extend standard roles with module-specific permissions. When you install a module, users already bound to the standard `view`, `edit`, or `admin` roles immediately gain the appropriate permissions for the module’s resources - no manual role updates are required.



## How Kyma Modules Use Aggregation

Kubernetes provides a `ClusterRole` aggregation mechanism that allows roles to automatically merge permissions from other roles based on label selectors. For details, see [Kubernetes: Aggregated ClusterRoles](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#aggregated-clusterroles).

Kyma modules use this mechanism to extend the standard Kubernetes `view`, `edit`, and `admin` roles. For example, to grant read-only access to the module's resources, a module provides the <code>kyma-<i class="varname">&lt;module&gt;</i>-view</code> role with label `rbac.authorization.k8s.io/aggregate-to-view: "true"`.

When you install a module, its permissions automatically merge into the standard roles. Users bound to `view`, `edit`, or `admin` roles immediately gain the appropriate module permissions.

> ### Tip:  
> To inspect which permissions a ClusterRole provides, use kubectl:
> 
> ```sh
> # List all module-provided roles
> kubectl get clusterrole | grep kyma- 
> # View a specific role's permissions
> kubectl get clusterrole kyma-telemetry-view -o yaml
> # See what's aggregated into the standard view role
> kubectl get clusterrole view -o yaml
> ```
> 
> The aggregated permissions appear in the `rules` section of the standard role.



## Module-Specific Roles

For information about Kyma modules and their features, see [Kyma Modules](../10-concepts/kyma-modules-0dda141.md).



### Istio

-   `kyma-istio-view` - Grants read-only access to the `Istio` custom resource.
-   `kyma-istio-edit` - Grants full access to the `Istio` custom resource.
-   `kyma-istio-resources-view` - Grants read-only access to resources from all API groups managed by Istio.
-   `kyma-istio-resources-edit` - Grants full access to resources from all API groups managed by Istio.



### API Gateway

-   `kyma-api-gateway-view` - Grants read-only access to API Gateway resources.
-   `kyma-api-gateway-edit` - Grants full access to API Gateway resources.



### SAP BTP Operator

-   `kyma-btp-operator-view` - Grants read-only access to BtpOperator, ServiceInstance, and ServiceBinding CRs and their status.
-   `kyma-btp-operator-edit` - Grants full access to BtpOperator, ServiceInstance, and ServiceBinding CRs and read-only access to their status.



### Keda

-   `kyma-keda-view` - Grants read-only access to the Keda custom resource and resources from all API groups managed by KEDA.
-   `kyma-keda-edit` - Grants full access to the Keda custom resource and resources from all API groups managed by KEDA.



### Eventing

-   `kyma-eventing-view` - Grants read-only access to all Eventing module custom resources and their statuses.
-   `kyma-eventing-edit` - Grants full access to all Eventing module custom resources and read-only access to their statuses.



### NATS

-   `kyma-nats-view` - Grants read-only access to the NATS custom resources and their statuses.
-   `kyma-nats-edit` - Grants full access to the NATS custom resources and read-only access to their statuses.



### Serverless

-   `kyma-serverless-view` - Grants read-only access to the Serverless custom resource.

-   `kyma-serverless-edit` - Grants full access to the Serverless custom resource.

-   `kyma-functions-view` - Grants read-only access to the Function custom resources.

-   `kyma-functions-edit` - Grants full access to the Function custom resources.




### Telemetry

-   `kyma-telemetry-view` - Grants read-only access to the Telemetry custom resources.

-   `kyma-telemetry-edit` - Grants write access to the Telemetry custom resources


