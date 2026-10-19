# Kubernetes assignment platform setup

Student ID: `02230135`

Application namespace: `usermgmt-02230135`

Application hostname: `usermgmt-02230135.local`

## Tools

Docker Desktop, VS Code, Git with Git Bash, kubectl, and minikube are installed on this computer. Minikube 1.39.0 stalled during cluster startup, so a checksum-verified minikube 1.38.1 executable is used for starting this cluster. Minikube 1.39.0 is used for its Traefik add-on. Run the following commands from this assignment folder in a new PowerShell terminal with Docker Desktop running in Linux-container mode.

```powershell
docker info
$assignmentMinikube = "$env:LOCALAPPDATA/KubernetesAssignment/tools/minikube-1.38.1/out/minikube-windows-amd64.exe"
& $assignmentMinikube start --driver=docker --cpus=2 --memory=4096 --kubernetes-version=v1.36.1 --preload=false --base-image=gcr.io/k8s-minikube/kicbase:v0.0.51 --cache-images=false
& $assignmentMinikube addons enable metrics-server
minikube addons enable traefik
kubectl --context=minikube apply -f k8s/00-namespace.yaml
```

These commands target a separate minikube cluster. Use `--context=minikube` with kubectl to avoid changing other clusters.

`--preload=false` avoids a stalled optional preload download encountered on this computer. Kubernetes still downloads its required images directly.

Changing `--native-ssh` did not fix the minikube 1.39.0 startup stall. The fallback version progressed past that step. It reports warnings because Kubernetes 1.36.1 and the v0.0.51 base image are newer than its supported defaults. Record this workaround when explaining the environment; do not assume compatibility for unrelated Kubernetes versions.

The fallback executable was downloaded from `https://github.com/kubernetes/minikube/releases/download/v1.38.1/minikube-windows-amd64.tar.gz`, extracted under `$env:LOCALAPPDATA/KubernetesAssignment/tools/minikube-1.38.1`, and verified against the official `minikube-windows-amd64.exe.sha256` file from the same release.

To speed up the first setup, the Kubernetes 1.36.1 binaries and images were copied from the existing local `dso202-control-plane` container. The binaries were verified against official SHA-256 files at `https://dl.k8s.io/release/v1.36.1/bin/linux/amd64/`. A fresh machine can download these files directly through minikube; it does not require that existing cluster. `--cache-images=false` disables minikube's host-side image cache, so Kubernetes can pull any missing images inside the node.

## Vertical Pod Autoscaler

In Git Bash, clone the official VPA source into a tools directory outside this assignment repository and install the pinned release:

```bash
git -c core.longpaths=true -c core.autocrlf=false clone --depth 1 --sparse --branch vertical-pod-autoscaler-1.8.0 https://github.com/kubernetes/autoscaler.git "$LOCALAPPDATA/KubernetesAssignment/tools/autoscaler"
git -C "$LOCALAPPDATA/KubernetesAssignment/tools/autoscaler" sparse-checkout set vertical-pod-autoscaler
cd "$LOCALAPPDATA/KubernetesAssignment/tools/autoscaler/vertical-pod-autoscaler"
kubectl config use-context minikube
MSYS2_ARG_CONV_EXCL='/CN=' ./hack/vpa-up.sh
```

The clone command is needed only once. If the directory already exists, use the existing checkout after verifying its tag.

## Verify the platform

```powershell
& $assignmentMinikube status
kubectl --context=minikube get nodes
kubectl --context=minikube get pods -A
kubectl --context=minikube get storageclass
kubectl --context=minikube top nodes
kubectl --context=minikube get namespace usermgmt-02230135
kubectl --context=minikube get ingressclass
kubectl --context=minikube get deployments -n kube-system
```

The node should be Ready. Traefik, metrics-server, and the VPA recommender, updater, and admission controller should be Running and Ready. The default StorageClass and its provisioner should be visible. Metrics may need some time before `kubectl top nodes` returns values.

This file covers platform prerequisites. The application, database, Ingress, HPA, and VPA workload manifests will be added in later milestones.

## Verified setup on 8 October 2026

- Node: Ready, Kubernetes v1.36.1.
- Docker container limits: 2 CPUs and 4 GiB memory.
- Namespace: usermgmt-02230135, applied from k8s/00-namespace.yaml.
- Ingress controller: Traefik, class traefik.
- Metrics: metrics-server Ready; kubectl top nodes returns CPU and memory values.
- StorageClass: standard (default), provisioner k8s.io/minikube-hostpath.
- VPA: v1.8.0 recommender, updater, and admission controller all Ready; webhook registered.
- Text evidence: evidence/M1-platform-verification.txt. Take screenshots of these commands as required by the assignment.
