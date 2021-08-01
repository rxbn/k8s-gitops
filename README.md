# k8s-gitops

![Kubernetes](https://i.imgur.com/p1RzXjQ.png)

## :loudspeaker:&nbsp; About

This repository contains my entire Kubernetes cluster setup built on K3s and managed by Flux v2.

## :wrench:&nbsp; Initial Deployment

1. Install K3s
2. Install Calico
3. Set GitHub token environment variable  
   `export GITHUB_TOKEN=SECRET`
4. Create `flux-system` namespace  
   `kubectl create namespace flux-system`
5. Apply sops secret  
   `kubectl apply -f sops-secret.yaml`
6. Bootstrap cluster  
   `flux bootstrap github --owner=rxbn --repository=k8s-gitops --personal --branch master --path core/ --network-policy=false`

## :leftwards_arrow_with_hook:&nbsp; Install pre-commit Hooks

`pre-commit install --hook-type pre-commit`

## :ballot_box_with_check:&nbsp; ToDo

- test renovate
- improve documentation
