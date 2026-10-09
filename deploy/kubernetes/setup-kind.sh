#!/usr/bin/env bash
# =============================================================================
# Setup Script for Kind Kubernetes Cluster & Tetragon eBPF Sensor
# =============================================================================
set -euo pipefail

CLUSTER_NAME="trust-lab-cluster"
MANIFESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/manifests"

echo "=== Runtime Trust Layer - Kubernetes Lab Setup ==="

# Check requirements
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is required but not installed."
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo "ERROR: kubectl is required but not installed."
    exit 1
fi

if ! command -v kind &> /dev/null; then
    echo "WARNING: kind is not in PATH. Please install kind: brew install kind"
    echo "For hosted/demo environments, Replay Mode is available out of the box."
    exit 0
fi

# Create Kind Cluster if not exists
if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "Kind cluster '${CLUSTER_NAME}' already exists."
else
    echo "Creating Kind cluster '${CLUSTER_NAME}'..."
    cat <<EOF | kind create cluster --name "${CLUSTER_NAME}" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraMounts:
  - hostPath: /sys/kernel/debug
    containerPath: /sys/kernel/debug
    readOnly: false
  - hostPath: /sys/fs/bpf
    containerPath: /sys/fs/bpf
    readOnly: false
- role: worker
  extraMounts:
  - hostPath: /sys/kernel/debug
    containerPath: /sys/kernel/debug
    readOnly: false
  - hostPath: /sys/fs/bpf
    containerPath: /sys/fs/bpf
    readOnly: false
EOF
fi

# Switch context
kubectl config use-context "kind-${CLUSTER_NAME}"

echo "Applying lab manifests..."
kubectl apply -f "${MANIFESTS_DIR}/01-namespace-sa.yaml"
kubectl apply -f "${MANIFESTS_DIR}/02-rbac.yaml"
kubectl apply -f "${MANIFESTS_DIR}/03-workloads.yaml"
kubectl apply -f "${MANIFESTS_DIR}/04-sensitive-data.yaml"
kubectl apply -f "${MANIFESTS_DIR}/05-network-policies.yaml"

# Check if Helm is available for Tetragon
if command -v helm &> /dev/null; then
    echo "Checking Tetragon eBPF sensor installation..."
    if ! helm list -n kube-system | grep -q "tetragon"; then
        echo "Installing Tetragon via Helm..."
        helm repo add cilium https://helm.cilium.io/ || true
        helm repo update
        helm install tetragon cilium/tetragon -n kube-system --wait || true
    fi
    kubectl apply -f "${MANIFESTS_DIR}/06-tetragon-policy.yaml" || true
else
    echo "Helm not found; skipping automated Tetragon chart install."
    echo "Events can be streamed via Replay Mode or standard Tetragon daemonset."
fi

echo "=== Lab Setup Complete ==="
kubectl get pods -n trust-lab
