<!-- loio148ae38b7d6f4e61bbb696bbfb3996b2 -->

# Assign Roles in the Kyma Environment

Kyma uses roles to manage access within the cluster, which give the assigned users the permissions suitable for their purposes.



<a name="loio148ae38b7d6f4e61bbb696bbfb3996b2__prereq_ehs_rvh_nsb"/>

## Prerequisites

The `cluster-admin` role is assigned to your account.

> ### Note:  
> After creating a Kyma cluster, you become an admin of this instance and the `cluster-admin` role is assigned to you by default. As the `cluster-admin`, you can assign roles to other users. Only the administrator who created the current subaccount can use the SAP BTP cockpit to assign the `cluster-admin` role to other members.



<a name="loio148ae38b7d6f4e61bbb696bbfb3996b2__context_lrm_lv2_hsb"/>

## Context

You can assign roles to a group of users only if you use a custom identity provider. Assigning roles in Kyma is based on the [Kubernetes role-based access control \(RBAC\)](https://kubernetes.io/docs/reference/access-authn-authz/rbac/). You can see the list of available roles in Kyma dashboard when you create a RoleBinding. Once you become the admin, your user name is read from the SAP BTP \(RBAC\) concept and is passed to the Kyma provisioner to be bound to the `cluster-admin` role in Kyma.

Kyma modules provide aggregated ClusterRoles that automatically extend the standard Kubernetes roles. For details about how aggregation works and how to inspect role permissions, see [ClusterRole Aggregation in Kyma](clusterrole-aggregation-in-kyma-33883dd.md).



<a name="loio148ae38b7d6f4e61bbb696bbfb3996b2__steps_bvs_hv2_hsb"/>

## Procedure

1.  Log in to Kyma dashboard. The URL is in the *Overview* section of your subaccount.

2.  In Kyma dashboard, select or create the namespace in which you want to assign roles.

3.  To create a role binding, go to *Configuration* \> *Role Bindings* \> *Create*. Fill in the required fields:

    1.  As *Name*, insert the name of your binding.

    2.  As *Role Type*, choose *ClusterRole*.

    3.  As *Role*, choose the required role from the list.

    4.  As *Kind*, choose *User*.

    5.  As *User name*, insert the user email address.


4.  Select *Create*.




<a name="loio148ae38b7d6f4e61bbb696bbfb3996b2__result_bx4_2v2_hsb"/>

## Results

The users have the required permissions within the specified namespace. If the users don't have additional cluster role binding to list the namespaces, they can still access the Kyma dashboard overview but must enter the required namespace name manually.



<a name="loio148ae38b7d6f4e61bbb696bbfb3996b2__postreq_rb5_ntn_fvb"/>

## Next Steps

If the permissions of the default role aren't sufficient, clone the role, and add the missing resources.

**Related Information**  


[Authorization in the Kyma Environment](authorization-in-the-kyma-environment-bb31080.md "You control access to your Kyma cluster using Kubernetes role-based access control (RBAC). Roles define what resources users can access and what actions they can perform.")

[ClusterRole Aggregation in Kyma](clusterrole-aggregation-in-kyma-33883dd.md "Kyma modules use Kubernetes ClusterRole aggregation to automatically extend standard roles with module-specific permissions. When you install a module, users already bound to the standard view, edit, or admin roles immediately gain the appropriate permissions for the module’s resources - no manual role updates are required.")

