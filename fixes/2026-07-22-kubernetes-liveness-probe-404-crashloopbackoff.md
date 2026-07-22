---
title: "CrashLoopBackOff on a healthy container: liveness probe hitting a path that did not exist"
date: 2026-07-22
tags: [kubernetes, kubelet, liveness-probe, nginx]
time: "20 minutes"
summary: "nginx was running perfectly. Kubernetes killed it four times in two minutes because the liveness probe checked a route the container never served."
environment: "k3s v1.30.0, 3 nodes (1 control plane, 2 workers)"
---

## Symptom

A deployment rolled out, the container reached `Running`, then flipped to
`CrashLoopBackOff` with the restart count climbing every few seconds.

```
NAME                            READY   STATUS             RESTARTS   AGE
nginx-6bd4c47c67-c69gc   0/1     CrashLoopBackOff   4          2m34s
```

The application logs showed no stack trace, no panic, and no exit error. That
combination is the interesting part: a container that is restarting without
crashing on its own is usually being killed by something else.

## What I checked first

`kubectl describe pod` before `kubectl logs`, because the events timeline tells
you who did what to the container, which logs cannot.

```
Normal   Pulled     Successfully pulled image "nginx:1.25"
Normal   Created    Created container nginx           (x4)
Normal   Started    Started container nginx           (x4)
Warning  Unhealthy  Liveness probe failed: HTTP probe failed with statuscode: 404   (x8)
Normal   Killing    Container nginx failed liveness probe, will be restarted        (x4)
```

Two things stand out. `Created` and `Started` succeeded four times, so the
container was starting cleanly every single time. And the failure reason is not
a crash, it is `Unhealthy` with a specific HTTP status code attached.

The container logs confirmed it from the other side:

```
[error] open() "/usr/share/nginx/html/healthz" failed (2: No such file or directory)
10.42.2.1 - - "GET /healthz HTTP/1.1" 404 153 "-" "kube-probe/1.30" "-"
[notice] 1#1: signal 3 (SIGQUIT) received, shutting down
```

The `kube-probe/1.30` user agent is the giveaway. That request came from the
kubelet's probe, not from a user, and the `SIGQUIT` immediately after is the
kubelet terminating the process.

## Root cause

The liveness probe was configured against `/healthz`:

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 80
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 2
```

The `nginx:1.25` image serves static files out of `/usr/share/nginx/html` and
has no route at `/healthz`, so it did the correct thing and returned 404.

The kubelet only treats an HTTP status in the 200 to 399 range as healthy.
Anything else counts as a probe failure. With `periodSeconds: 5` and
`failureThreshold: 2`, two consecutive 404s ten seconds apart were enough for
the kubelet to declare a perfectly healthy process dead and restart it. The
restart re-ran the same probe against the same missing path, which is why it
looped.

CrashLoopBackOff here never meant "the app crashed". It meant "Kubernetes killed
this container repeatedly, and is now backing off between restarts".

## The fix

Point the probe at a route the container actually serves:

```bash
kubectl patch deployment nginx -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"nginx",
    "livenessProbe":{"httpGet":{"path":"/","port":80},
    "initialDelaySeconds":5,"periodSeconds":5,"failureThreshold":2}}]}}}}'
```

Restart count stopped climbing and the pod settled into `Running`.

## Why it happened

`/healthz` is a convention, not a default. It comes from the Kubernetes
ecosystem itself, where components expose a dedicated lightweight health
endpoint under that path, and it gets copied between manifests constantly. The
mistake is assuming the convention is implemented by every image. It is a path
your application has to actually serve, and nginx out of the box does not.

Serving `/` is the correct fix for this specific container, but it is not the
pattern I would ship for a real application. A homepage often depends on
downstream services, so probing it means an unrelated outage can make Kubernetes
kill healthy pods. The production pattern is a dedicated endpoint that returns
200 based only on the state of the process itself, with dependency checks kept
in the readiness probe where a failure removes the pod from load balancing
instead of destroying it.

## What I changed so it does not happen again

Added a check to the manifest validation stage of the pipeline: if a container
declares an `httpGet` liveness probe, the path must appear in that service's
documented routes. A missing route now fails the merge request instead of
reaching a cluster and looking like an application crash.
