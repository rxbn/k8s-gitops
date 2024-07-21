# base/monitoring Directory

This directory contains monitoring apps.

## Contents

- **cloudnative-pg** contains monitoring objects for Cloud Native PostgreSQL
- **flux-system** contains monitoring objects for Flux. They need to be created afterwards since crds don't exist when `core` is being deployed.
- **kube-prometheus-stack** is a collection of Kubernetes manifests, Grafana dashboards, and Prometheus rules
- **prometheus-pushgateway** is a push acceptor for ephemeral and batch jobs
