# k8s-gitops

![Kubernetes](https://i.imgur.com/p1RzXjQ.png)

## :loudspeaker:&nbsp; About

This repository contains my entire Kubernetes cluster setup built on K3s and managed by Flux v2.

## :leftwards_arrow_with_hook:&nbsp; Install pre-commit Hooks

`pre-commit install --hook-type pre-commit`

## :wrench:&nbsp; Initial Deployment

1. Install K3s
2. Install Calico
3. Create `flux-system` namespace  
   `kubectl create namespace flux-system`
4. Apply sops secret  
   `kubectl apply -f sops-secret.yaml`
5. Bootstrap cluster  
   `kubectl apply --kustomize=./core/flux-system`

## :ballot_box_with_check:&nbsp; ToDo

- test renovate
- improve documentation
- test and improve `sync cloudflare network ranges` Github Action

## :hugs:&nbsp; Thanks

Thanks to the community at [k8s@home](https://github.com/k8s-at-home) for the awesome templates and the Kubernetes at home logo!
