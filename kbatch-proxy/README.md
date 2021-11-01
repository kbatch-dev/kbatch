# kbatch-proxy

A simple Kubernetes proxy, allowing JupyterHub users to make requests to the Kubernetes API without having direct access to the Kubernetes API.

## Motivation

We want `kbatch` users to be able to create Kubernetes Jobs, access logs, etc., but

1. Don't want to grant them *direct* access to the Kubernetes API
2. Don't want to maintain a separate web application, with any state that's independent of Kubernetes

Enter `kbatch-proxy`

## Design

A simple FastAPI application that sits in between `kbatch` users and the Kubernetes API. It's expected that the `kbatch-proxy`
application has access to the Kubernetes API, with permission to create namespaces, jobs, etc. This will often be run as a JupyterHub service.

Users will make requests to `kbatch-proxy`. Upon request we will

1. Validate that the user is authenticated with JupyterHub (checking the `Bearer` token)
2. Validate that data the user is submitting or requesting meets our [security model](#security-model)
3. Make the request to the Kubernetes API on behalf of the user

## Security model

This remains to be proven effective, but the hope is to let users do whatever they want in their own namespace and nothing outside of their namespace.