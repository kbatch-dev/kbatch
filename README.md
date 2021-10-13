# kbatch

Submit batch jobs.

## Architecture

Because end-users don't have access to the Kubernetes API, we have a client/server model. Users make API requests to the server to submit / list / show jobs.

The server is split into two parts: a frontend that handles requests, and a backend that submits them to Kubernetes.

## Usage

Authenticate with the server

```
$ kbatch login https://url-to-kbatch-server
```

This will create configuration file that specifies the default URL and credentials to use for all `kbatch` operations.

Submit a job

```
$ kbatch submit myscript.py --image=...
...
```

List jobs

```
$ kbatch jobs list
...
```

Show the detail on a given job

```
$ kbatch jobs show --job-id=...
```

List available images

```
$ kbatch images list
```