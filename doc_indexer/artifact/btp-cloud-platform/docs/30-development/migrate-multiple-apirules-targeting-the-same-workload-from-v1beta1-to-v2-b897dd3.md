<!-- loiob897dd34bf4449d5a9fff6943191e1ab -->

# Migrate Multiple `APIRule`s Targeting the Same Workload from *v1beta1* to *v2*

Learn how to migrate multiple `APIRule`s *v1beta1* that expose the same workload using different host names. To keep all endpoints available during migration, you must create an additional, temporary `AuthorizationPolicy`. This ensures that service requests to `APIRule`s *v1beta1* are handled as intended, while another `APIRule` targeting the same workload has already been migrated to *v2*.



<a name="loiob897dd34bf4449d5a9fff6943191e1ab__context_multiple_apirules"/>

## Context

When you have multiple `APIRule`s *v1beta1* that expose the same workload but use different host values, and you migrate only one of those `APIRule`s to version *v2*, you may get ***HTTP/2 403 RBAC: Access Denied*** errors when making requests to the endpoints of the remaining *v1beta1* `APIRule`s. However, requests to the endpoint of the migrated *v2* `APIRule` are successful, returning ***HTTP/2 200 OK*** responses.

***HTTP/2 403 RBAC: Access Denied*** errors are caused by Istio subresources created by the migrated `APIRule` *v2*. Because the other `APIRule`s exposing the same workload remain in version *v1beta1* and do not use Istio subresources, requests from these `APIRule`s *v1beta1* to the workload are no longer allowed. In such cases, access to the target workload is permitted only for requests that match the rules specified in the `APIRule` *v2*.

For example, suppose a scenario where you have applied the following two *v1beta1* `APIRule`s configured to expose the same HTTPBin Service, each with a different host value, and you want to maintain uninterrupted access to service endpoints during migration.

```
apiVersion: gateway.kyma-project.io/v1beta1
kind: APIRule
metadata:
  name: example1
  namespace: test
spec:
  host: example1
  service:
    name: httpbin
    namespace: default
    port: 8000
  gateway: kyma-gateway.kyma-system
  rules:
    - path: /post
      methods: ["POST"]
      accessStrategies:
        - handler: no_auth
    - path: /.*
      methods: ["GET"]
      mutators: []
      accessStrategies:
        - handler: jwt
          config:
            trusted_issuers:
              - https://{IAS_TENANT}.accounts.ondemand.com
            jwks_urls:
              - https://{IAS_TENANT}.accounts.ondemand.com/oauth2/certs
---
apiVersion: gateway.kyma-project.io/v1beta1
kind: APIRule
metadata:
  name: example2
  namespace: test
spec:
  host: example2
  service:
    name: httpbin
    namespace: default
    port: 8000
  gateway: kyma-gateway.kyma-system
  rules:
    - path: /post
      methods: ["POST"]
      accessStrategies:
        - handler: no_auth
    - path: /.*
      methods: ["GET"]
      mutators: []
      accessStrategies:
        - handler: jwt
          config:
            trusted_issuers:
              - https://{IAS_TENANT}.accounts.ondemand.com
            jwks_urls:
              - https://{IAS_TENANT}.accounts.ondemand.com/oauth2/certs
```

To ensure a seamless migration to *v2* without any downtime, you must create an additional, temporary `AuthorizationPolicy` before applying the first migrated `APIRule` *v2*.

> ### Note:  
> Using both versions of `APIRule`s for one target workload is not recommended. Instead, migrate all `APIRule`s targeting the same workload at once to version *v2*. Creating a temporary `AuthorizationPolicy` blocks internal traffic to the workload, which migration to `APIRule` *v2* causes anyway. We recommend the following course of action:
> 
> 1.  Apply the temporary `AuthorizationPolicy` that blocks in-cluster communication and unblocks *v1beta1* exposure to external traffic during the migration.
> 2.  Migrate `APIRule`s to *v2*. For instructions, follow the migration guidelines.
> 3.  Delete the temporary `AuthorizationPolicy`.



## Procedure

1.  For each of your `APIRule`s *v1beta1* targeting the same workload, list hosts that contain at least one *allow* or *no\_auth* handler. Specify those hosts in the FQDN format.

    > ### Note:  
    > If your `APIRule`s *v1beta1* don't use the *allow* or *no\_auth* handlers, skip this step. Specifying these hosts is only necessary for `APIRule`s with *allow* or *no\_auth* access strategies to allow traffic from Istio ingress gateway to the target workload during migration. Other handlers, such as *jwt*, *oauth2\_introspection*, and *noop*, use the Ory Oathkeeper service, and the traffic doesn't come directly from the ingress gateway to the target workload.

    In the example, two `APIRule`s *v1beta1* with *no\_auth* handler expose the same `httpbin` Service on different hosts: `example1` and `example2`.

    To obtain the FQDN format of the hosts, get the domain of the referenced Gateway:

    ```
    kubectl get gateway <GATEWAY_NAME> -n <GATEWAY_NAMESPACE> -o jsonpath='{.spec.servers[0].hosts}'
    ```

    In the example scenario, the command looks like this:

    ```
    kubectl get gateway -n kyma-system kyma-gateway -o jsonpath='{.spec.servers[0].hosts}'
    ["*.local.kyma.dev"]%
    ```

    Assuming the default domain is `local.kyma.dev`, the FQDN format of the hosts is:

    -   `example1.local.kyma.dev`
    -   `example2.local.kyma.dev`

2.  To identify the label key and value for the target workload, check the selector from the Service that the `APIRule`s expose.

    ```
    kubectl get service <SERVICE_NAME> -n <NAMESPACE> -o jsonpath='{.spec.selector}'
    ```

    In the example, the selector for the `httpbin` Service in the `default` namespace is `app: httpbin`:

    ```
    kubectl get service httpbin -n default -o jsonpath='{.spec.selector}'
    {"app":"httpbin"}%
    ```

3.  Create a temporary `AuthorizationPolicy` using the gathered information in the previous steps.


    <table>
    <tr>
    <th valign="top">

    Option
    
    </th>
    <th valign="top">

    Description
    
    </th>
    </tr>
    <tr>
    <td valign="top">
    
    `{NAMESPACE}`
    
    </td>
    <td valign="top">
    
    The namespace to which the `AuthorizationPolicy` applies. This namespace must include the target workload for which you allow traffic. The selector matches workloads in the same namespace as the `AuthorizationPolicy`.
    
    </td>
    </tr>
    <tr>
    <td valign="top">
    
    `{HOSTNAME}`
    
    </td>
    <td valign="top">
    
    List all host names that are exposed by the *v1beta1* `APIRule`s being migrated which contain handler *no\_auth* or *allow*. List all relevant hostnames in FQDN format.
    
    </td>
    </tr>
    <tr>
    <td valign="top">
    
    `{LABEL_KEY}`: `{LABEL_VALUE}`
    
    </td>
    <td valign="top">
    
    Specify label selectors that match the target workload. For more information, see [Authorization Policy](https://istio.io/latest/docs/reference/config/security/authorization-policy/).
    
    </td>
    </tr>
    </table>
    
    This `AuthorizationPolicy` allows traffic from the Ory Oathkeeper service and the Istio ingress gateway to the target workload only for the specified hosts. Applying this `AuthorizationPolicy` before starting the migration process ensures uninterrupted access to service endpoints during the migration.

    ```
    apiVersion: security.istio.io/v1
    kind: AuthorizationPolicy
    metadata:
      name: allow-migration
      namespace: {NAMESPACE}
    spec:
      action: ALLOW
      rules:
        - from:
            - source:
                principals:
                  - "cluster.local/ns/kyma-system/sa/oathkeeper-maester-account"
        - from:
            - source:
                principals:
                  - "cluster.local/ns/istio-system/sa/istio-ingressgateway-service-account"
          to:
            - operation:
                hosts:
                  - {HOSTNAME1}
                  - {HOSTNAME2}
      selector:
        matchLabels:
          {LABEL_KEY}: {LABEL_VALUE}
    ```

    If you don't migrate any `APIRule`s *v1beta1* with *allow* or *no\_auth* handlers, remove the second rule from the `AuthorizationPolicy`. The `AuthorizationPolicy` then allows all traffic from the Ory Oathkeeper service to the target workload.

    ```
    apiVersion: security.istio.io/v1
    kind: AuthorizationPolicy
    metadata:
      name: allow-migration
      namespace: {NAMESPACE}
    spec:
      action: ALLOW
      rules:
        - from:
            - source:
                principals:
                  - "cluster.local/ns/kyma-system/sa/oathkeeper-maester-account"
      selector:
        matchLabels:
          {LABEL_KEY}: {LABEL_VALUE}
    ```

    If you migrate `APIRule`s *v1beta1* that specify only the *allow* or *no\_auth* handlers, remove the first rule from the `AuthorizationPolicy`:

    ```
    apiVersion: security.istio.io/v1
    kind: AuthorizationPolicy
    metadata:
      name: allow-migration
      namespace: {NAMESPACE}
    spec:
      action: ALLOW
      rules:
        - from:
            - source:
                principals:
                  - "cluster.local/ns/istio-system/sa/istio-ingressgateway-service-account"
          to:
            - operation:
                hosts:
                  - {HOSTNAME1}
                  - {HOSTNAME2}
      selector:
        matchLabels:
          {LABEL_KEY}: {LABEL_VALUE}
    ```

    In the example scenario, `APIRule`s *v1beta1* specify both *no\_auth* and *jwt* handlers. Therefore, the temporarily applied `AuthorizationPolicy` looks like this:

    ```
    apiVersion: security.istio.io/v1
    kind: AuthorizationPolicy
    metadata:
      name: allow-migration
      namespace: test
    spec:
      action: ALLOW
      rules:
        - from:
            - source:
                principals:
                  - "cluster.local/ns/kyma-system/sa/oathkeeper-maester-account"
        - from:
            - source:
                principals:
                  - "cluster.local/ns/istio-system/sa/istio-ingressgateway-service-account"
          to:
            - operation:
                hosts:
                  - example1.local.kyma.dev
                  - example2.local.kyma.dev
      selector:
        matchLabels:
          app: httpbin
    ```

4.  To migrate `APIRule`s *v1beta1* to *v2*, follow the steps in the migration guidelines. During this process, the temporary `AuthorizationPolicy` ensures that requests from both *v1beta1* `APIRule`s to the target workload are allowed.

    See [Migrate APIRule from Version v1beta1 to Version v2](migrate-apirule-from-version-v1beta1-to-version-v2-f8df238.md).

5.  After all `APIRule`s targeting the same workload are migrated to *v2*, delete the temporary `AuthorizationPolicy`.

    ```
    kubectl delete authorizationpolicy <AUTHORIZATION_POLICY_NAME> -n <NAMESPACE>
    ```

    See an example:

    ```
    kubectl delete authorizationpolicy allow-migration -n default
    ```


