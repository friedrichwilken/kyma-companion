<!-- loio2e4426bd276d458c8a8c7f89e185f6ac -->

# Service Instance Not Updated When Watched Parameters Secret Is Modified



<a name="loio2e4426bd276d458c8a8c7f89e185f6ac__section_symptom_fgp"/>

## Symptom

You have a service instance configured with `parametersFrom` referencing your parameters Secret \(see [Passing Parameters](passing-parameters-2cfd47c.md)\) and `watchParametersFromChanges` set to *true*, but updating the Secret does not trigger an update of the service instance.



<a name="loio2e4426bd276d458c8a8c7f89e185f6ac__section_cause_hkl"/>

## Cause

The SAP BTP service operator uses limited cache mode, which is enabled by default in the SAP BTP Operator module. In this mode, the operator only watches Secrets that carry the label `services.cloud.sap.com/managed-by-sap-btp-operator: "true"`. A Secret without this label is not tracked, so changes to it go undetected — no update is triggered and no error is reported.



<a name="loio2e4426bd276d458c8a8c7f89e185f6ac__section_solution_mnq"/>

## Solution

Add the label `services.cloud.sap.com/managed-by-sap-btp-operator: "true"` to the parameters Secret. Choose one of the following methods:

-   Run the following kubectl command:

    ```
    kubectl label secret <SECRET_NAME> -n <NAMESPACE> services.cloud.sap.com/managed-by-sap-btp-operator=true
    ```

-   Include the label in your Secret manifest:

    ```
    apiVersion: v1
    kind: Secret
    metadata:
      name: <SECRET_NAME>
      namespace: <NAMESPACE>
      labels:
        services.cloud.sap.com/managed-by-sap-btp-operator: "true"
    type: Opaque
    stringData:
      secret-parameter: |
        {
          "key": "value"
        }
    ```


When the label is present, the SAP BTP service operator detects it immediately and reconciles the service instance on the next Secret change. You don't need to wait or restart the operator.

