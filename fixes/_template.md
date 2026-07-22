---
title: "Short, specific, includes the actual error text"
date: 2026-07-22
tags: [kubernetes, kubectl]
time: "25 minutes"
summary: "One sentence a recruiter can read in three seconds. What broke and what the real cause was."
environment: "k3s v1.30, 3 nodes"
draft: true
---

## Symptom

What you actually saw. Paste the real output, not a description of it.

```
kubectl get pods
NAME                   READY   STATUS             RESTARTS   AGE
app-6bd4c47c67-c69gc   0/1     CrashLoopBackOff   4          2m
```

## What I checked first

The order you looked in, including the dead ends. Dead ends are worth keeping.
They show how you narrow a problem instead of jumping to an answer.

## Root cause

The actual mechanism, not the symptom. "The probe path did not exist" is a
symptom. "The kubelet treats any non-2xx as a failure, so nginx correctly
returning 404 for a path that was never configured was read as a dead process"
is a root cause.

## The fix

```bash
kubectl patch deployment app -p '...'
```

## Why it happened

The design or process reason. This is the part that turns a fix into a story
you can tell in an interview.

## What I changed so it does not happen again

The systemic fix: a validation step, a template default, a CI check, an alert.
If there is no systemic fix, say so and explain why.
