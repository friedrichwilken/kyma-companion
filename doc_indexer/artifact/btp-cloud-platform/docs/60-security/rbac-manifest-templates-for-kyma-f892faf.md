<!-- loiof892faf6467b43648fbc69f46efd832f -->

# RBAC Manifest Templates for Kyma

Use the following manifest templates to implement the recommended RBAC \(Kubernetes role-based access control\) patterns in your Kyma cluster.



1.  Before applying the manifests, replace placeholder values \(in angle brackets\) with your actual configuration.

2.  To apply a template, run `kubectl apply -f` `filename.yaml`.




### Impersonation in Kubernetes

With Kubernetes [User Impersonation](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#user-impersonation), you can enable a least-privilege type of access to the Kubernetes cluster. With this feature, a subject \(that is, users, groups, or service accounts\) can acquire another Kubernetes user or group identity. These acquired identities are called “virtual users” or “vUser” because they don't need to exist.

Just create a ClusterRoleBinding that contains a virtual user \(`vUserName`\) and the administrative ClusterRole. For example, the operator or developer is allowed to impersonate the virtual user to perform administrative tasks.

![](images/Kubernetes_Impersonation_f6426e5.svg)



<a name="loiof892faf6467b43648fbc69f46efd832f__section_recommended_role_setup"/>

## Recommended Role Setup



### Operators

-   By default, operators only have view access in the clusters.
-   By impersonating a virtual user \(`cluster-admin`\) bound to the ClusterRole `cluster-admin`, the operator can perform administrative tasks.

  
  
**Role Setup: Operators in Dev, Test, and Prod**

![](images/Role_Concept_Operator_All_392ef0f.svg "Role Setup: Operators in Dev, Test, and Prod")



### Developers

-   In Dev and Test clusters, developers have full access to their namespaces. In the namespace, bind them to the ClusterRole `admin`.
-   In Prod clusters, developers only have view access to their namespace. In the namespace, bind them to the ClusterRole `cluster-viewer`.
-   By impersonating a virtual user \(`app-admin`\) bound to the ClusterRole `admin`, a developer can perform administrative tasks in their namespace.
-   Developers typically also need read-only access to cluster-level resources in other namespaces, such as “Istio” or “Application Connector” configurations. Bind them to the ClusterRole `view` for this \(see also the generic role template “View Common Kyma Objects in the Cluster”\).

  
  
**Role Setup: Developers in Dev and Test**

![](images/Role_Concept_Developer_DevTest_4e24b33.svg "Role Setup: Developers in Dev and Test")

  
  
**Role Setup: Developers in Prod**

![](images/Role_Concept_Developer_PROD_8dccb86.svg "Role Setup: Developers in Prod")

To implement these patterns in your cluster, create RoleBindings and ClusterRoleBindings for your users and groups. For details, see [Assign Roles in the Kyma Environment](assign-roles-in-the-kyma-environment-148ae38.md).



<a name="loiof892faf6467b43648fbc69f46efd832f__section_kyma_kubernetes_manifest_templates_generic"/>

## Kubernetes Manifest Templates for Generic Roles



### View All Resources

Used in **Dev**, **Test**, and **Prod** clusters:

-   ClusterRole `cluster-viewer`

    > ### Sample Code:  
    > ```
    > # ClusterRole with the permission to view all resources
    > kind: ClusterRole
    > apiVersion: rbac.authorization.k8s.io/v1
    > metadata:
    >   name: cluster-viewer
    > rules:
    >   - apiGroups: ['*']
    >     verbs: ['get', 'list', 'watch']
    >     resources: ['*']
    > ```




### View Common Kyma Objects in the Cluster

Used in **Dev**, **Test**, and **Prod** clusters:

-   ClusterRole `common-resource-viewer`

    > ### Sample Code:  
    > ```
    > # ClusterRole with the permissions to view common Kyma objects in the cluster
    > apiVersion: rbac.authorization.k8s.io/v1
    > kind: ClusterRole
    > metadata:
    >   name: <common-resource-viewer>
    > rules:
    >   - verbs:
    >       - get
    >       - list
    >       - watch
    >     apiGroups:
    >       - applicationconnector.kyma-project.io
    >       - networking.istio.io
    >     resources:
    >       - applications
    >       - gateways
    >     resourceNames: []
    >     nonResourceURLs: []
    > ```

-   ClusterRoleBinding `common-resource-viewer-crb`

    > ### Sample Code:  
    > ```
    > # ClusterRoleBinding to allow a group to view common Kyma objects in the cluster
    > apiVersion: rbac.authorization.k8s.io/v1
    > kind: ClusterRoleBinding
    > metadata:
    >   name: <common-resource-viewer-crb>
    > subjects:
    >   - kind: Group
    >     name: <group-name>
    >     apiGroup: rbac.authorization.k8s.io
    > roleRef:
    >   kind: ClusterRole
    >   name: common-resource-viewer
    >   apiGroup: rbac.authorization.k8s.io
    > 
    > ```




<a name="loiof892faf6467b43648fbc69f46efd832f__section_kyma_kubernetes_manifest_templates_operators"/>

## Kubernetes Manifest Templates for Operators



### View Access for All Clusters

Used in **Dev**, **Test**, and **Prod** clusters:

-   ClusterRoleBinding `cluster-admin-view-crb`

    > ### Sample Code:  
    > ```
    > # Default permissions for the ops-team group to view all resources in the cluster
    > apiVersion: rbac.authorization.k8s.io/v1
    > kind: ClusterRoleBinding
    > metadata:
    >   name: cluster-admin-view-crb
    > roleRef:
    >   apiGroup: rbac.authorization.k8s.io
    >   kind: ClusterRole
    >   name: cluster-viewer
    > subjects:
    >   - apiGroup: rbac.authorization.k8s.io
    >     kind: Group
    >     name: <group-name>
    > 
    > ```




### Admin Access for All Clusters

Used in **Dev**, **Test**, and **Prod** clusters:

-   ClusterRoleBinding `cluster-admin-crb`

    > ### Note:  
    > The ClusterRole `cluster-admin` isn't directly bound to the group of the operations team; they can only impersonate it.

    > ### Sample Code:  
    > ```
    > # ClusterRoleBinding to allow the (not really existing) user cluster-admin to have cluster-admin permissions on the cluster. The ClusterRole cluster-admin is NOT directly bound to the ops-team group.
    > apiVersion: rbac.authorization.k8s.io/v1
    > kind: ClusterRoleBinding
    > metadata:
    >   name: cluster-admin-crb
    > roleRef:
    >   apiGroup: rbac.authorization.k8s.io
    >   kind: ClusterRole
    >   name: cluster-admin
    > subjects:
    >   - apiGroup: rbac.authorization.k8s.io
    >     kind: User
    >     name: cluster-admin
    > 
    > ```

-   ClusterRole `cluster-admin-impersonator`

    > ### Sample Code:  
    > ```
    > # ClusterRole to allow the impersonation of the cluster-admin user
    > 
    > apiVersion: rbac.authorization.k8s.io/v1
    > kind: ClusterRole
    > metadata:
    >   name: cluster-admin-impersonator
    > rules:
    >   - apiGroups: ['']
    >     resources: ['users']
    >     verbs: ['impersonate']
    >     resourceNames: ['cluster-admin']
    > 
    > ```

-   ClusterRoleBinding `cluster-admin-impersonate-crb`

    > ### Sample Code:  
    > ```
    > # ClusterRoleBinding to bind the impersonation capability to everyone in the ops-team group
    > apiVersion: rbac.authorization.k8s.io/v1
    > kind: ClusterRoleBinding
    > metadata:
    >   name: cluster-admin-impersonate-crb
    > roleRef:
    >   apiGroup: rbac.authorization.k8s.io
    >   kind: ClusterRole
    >   name: cluster-admin-impersonator
    > subjects:
    >   - apiGroup: rbac.authorization.k8s.io
    >     kind: Group
    >     name: <group-name>
    > ```




<a name="loiof892faf6467b43648fbc69f46efd832f__section_kyma_kubernetes_manifest_templates_developers"/>

## Kubernetes Manifest Templates for Developers



### Namespace Admin Access for Dev and Test

Used in **Dev** and **Test** clusters:

-   RoleBinding `admin`

    > ### Sample Code:  
    > ```
    > 
    > apiVersion: rbac.authorization.k8s.io/v1
    > kind: RoleBinding
    > metadata:
    >   name: <name>
    >   namespace: <name of the namespace>
    > subjects:
    >   - kind: Group
    >     name: <group name>
    >     apiGroup: rbac.authorization.k8s.io
    > roleRef:
    >   kind: ClusterRole
    >   name: admin
    >   apiGroup: rbac.authorization.k8s.io
    > 
    > ```




### Admin Access for Prod

Create the respective manifest files for each team and namespace, and adapt them accordingly.

Used in **Prod** clusters:

-   ClusterRole `app-admin-impersonator`

    > ### Sample Code:  
    > ```
    > # ClusterRole to allow the impersonation of the application admin user
    > apiVersion: rbac.authorization.k8s.io/v1
    > kind: ClusterRole
    > metadata:
    >   name: <app-admin-impersonator>
    > rules:
    >   - apiGroups: ['']
    >     resources: ['users']
    >     verbs: ['impersonate']
    >     resourceNames: ['<name of the virtual user>']
    > 
    > ```

-   ClusterRoleBinding `app-team-impersonation-crb`

    > ### Sample Code:  
    > ```
    > # ClusterRoleBinding to bind the impersonation capability to the app-team group
    > apiVersion: rbac.authorization.k8s.io/v1
    > kind: ClusterRoleBinding
    > metadata:
    >   name: <app-team-impersonation-crb>
    > roleRef:
    >   apiGroup: rbac.authorization.k8s.io
    >   kind: ClusterRole
    >   name: <app-admin-impersonator>
    > subjects:
    >   - apiGroup: rbac.authorization.k8s.io
    >     kind: Group
    >     name: <group-name>
    > 
    > ```

-   RoleBinding `admin`

    > ### Note:  
    > The ClusterRole `admin` isn't directly bound to the groups of the development teams; they can only impersonate it.

    > ### Sample Code:  
    > ```
    > # RoleBinding to allow a (not really existing) user to have admin permissions in a specific namespace. The ClusterRole admin is NOT directly bound to the developers groups.
    > apiVersion: rbac.authorization.k8s.io/v1
    > kind: RoleBinding
    > metadata:
    >   name: <binding name, e.g. app1-admin-crb>
    >   namespace: <namespace>
    > roleRef:
    >   apiGroup: rbac.authorization.k8s.io
    >   kind: ClusterRole
    >   name: admin
    > subjects:
    >   - apiGroup: rbac.authorization.k8s.io
    >     kind: User
    >     name: <name of the virtual user>
    > 
    > ```




### Read Access to Namespace for Prod

Create the respective manifest files for each team and namespace, and adapt them accordingly.

Used in **Prod** clusters:

-   RoleBinding `cluster-viewer`

    > ### Sample Code:  
    > ```
    > # Default permissions of an app-team group to view all resources in a dedicated namespace
    > apiVersion: rbac.authorization.k8s.io/v1
    > kind: RoleBinding
    > metadata:
    >   name: <namespace-viewer-binding>
    >   namespace: <namespace>
    > roleRef:
    >   apiGroup: rbac.authorization.k8s.io
    >   kind: ClusterRole
    >   name: cluster-viewer
    > subjects:
    >   - apiGroup: rbac.authorization.k8s.io
    >     kind: Group
    >     name: <group-name>
    > 
    > ```


