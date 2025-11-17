# k8s-gitops

![Kubernetes](https://i.imgur.com/p1RzXjQ.png)

## :loudspeaker:&nbsp; About

This repository contains my entire Kubernetes cluster setup built on K3s and managed by Flux v2.\
Secrets are encrypted and managed with [SOPS](https://github.com/mozilla/sops).

## :open_file_folder:&nbsp; Repository Structure

This Git Repository contains the following directories and are ordered below by how Flux will apply them:

- **core** directory is where Flux deployments are located
- **crds** directory (depends on **core**) contains CustomResourceDefinitions that need to exist before anything else
- **infra** directory (depends on **crds**) contains infrastructure applications such as ingress-nginx, Envoy Gateway, MetalLB and so on
- **base** directory (depends on **infra**) contains applications that are useful for cluster operations such as kube-prometheus-stack, K8up and so on
- **apps** directory (depends on **base**) is where common applications are located

These directories are not tracked by Flux but are useful nonetheless:

- **.github** directory contains GitHub related files
- **.taskfiles** directory contains go-tasks
- **hack** directory contains useful scrips

## :leftwards_arrow_with_hook:&nbsp; Install pre-commit Hooks

Install all pre-commit hooks so they are executed every time before a commit occurs.

`pre-commit install --hook-type pre-commit`

## :wrench:&nbsp; Initial Deployment

1. Install K3s
2. Install Cilium
3. Create `flux-system` namespace\
   `kubectl create namespace flux-system`
4. Apply sops private key secret\
   `kubectl apply -f sops-secret.yaml`
5. Apply cluster-settings configmap\
   `kubectl apply -f core/cluster-settings.yaml`
6. Bootstrap cluster (may needs to be executed twice)\
   `kubectl apply --kustomize=./core/flux-system`

## :robot:&nbsp; Automation

- [Renovate](https://www.whitesourcesoftware.com/free-developer-tools/renovate) is a very useful tool that when configured will start to create PRs in your GitHub repository when Docker images, Helm charts or anything else that can be tracked has a newer version. The configuration for Renovate is located [here](./.github/renovate.json)

There are also a couple GitHub workflows included in this repository that will help automate some processes.

- [Sync Cloudflare network ranges](./.github/workflows/sync-cloudflare-nets.yaml) - workflow to update Cloudflare network ranges
- [Diff HelmReleases on Pull Requests](./.github/workflows/helm-release-differ.yaml) - workflow to add diff to `HelmRelease` pull requests

## :hugs:&nbsp; Thanks

Huge thanks to the community at [k8s@home](https://github.com/k8s-at-home) for the awesome templates and the Kubernetes at home logo!
