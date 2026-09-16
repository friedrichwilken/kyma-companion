<!-- loiobb31080fd0474d38a050e32a7a7ed629 -->

# Authorization in the Kyma Environment

You control access to your Kyma cluster using Kubernetes role-based access control \(RBAC\). Roles define what resources users can access and what actions they can perform.



<a name="loiobb31080fd0474d38a050e32a7a7ed629__section_standard_roles"/>

## Standard Roles

For access management, Kyma relies on standard Kubernetes RBAC, using standard Kubernetes ClusterRoles with different levels of access: `view`, `edit`, `admin`, and `cluster-admin`. For details, see [Kubernetes: User-facing roles](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#user-facing-roles).

When you create a Kyma cluster, your user account is automatically bound to the `cluster-admin` role. As a cluster admin, you can assign roles to other users and groups.

You manage roles and bindings directly in the cluster using Kyma dashboard or kubectl. You don't use SAP BTP role collections for this task.

You assign roles to users or groups through RoleBindings \(scoped to a namespace\) and ClusterRoleBindings \(scoped to the entire cluster\). To assign roles to groups rather than individual users, you must configure a custom identity provider. The default shared SAP ID service tenant does not support group claims. For details, see [Authentication in the Kyma Environment](authentication-in-the-kyma-environment-85200d8.md).

As a starting point, separate operators from developers: operators manage the cluster infrastructure, and developers work within their namespaces. If you want to avoid permanent assignment of powerful roles, use Kubernetes impersonation. For details and manifest templates, see [RBAC Manifest Templates for Kyma](rbac-manifest-templates-for-kyma-f892faf.md).



## Module Permissions

Kyma modules automatically extend the standard `view`, `edit`, and `admin` roles with module-specific permissions through ClusterRole aggregation. When you install a module, users assigned to these roles immediately get the appropriate module permissions. You don't have to update the roles manually. For details, see [ClusterRole Aggregation in Kyma](clusterrole-aggregation-in-kyma-33883dd.md).

**Related Information**  


[Kubernetes: Using RBAC Authorization](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

[Kubernetes: Role Based Access Control Good Practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/)

