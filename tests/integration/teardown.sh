#!/usr/bin/env bash

# standard bash error handling
set -o nounset  # treat unset variables as an error and exit immediately.
set -o errexit  # exit immediately when a command fails.
set -E          # needs to be set if we want the ERR trap
set -o pipefail # prevents errors in a pipeline from being masked

# delete integration test fixtures.
kubectl delete -f ./tests/integration/fixtures/.

# delete k3d cluster.
k3d cluster delete --config ./tests/integration/k3d-config.yaml
