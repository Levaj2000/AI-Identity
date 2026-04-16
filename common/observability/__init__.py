"""Observability — Prometheus metrics + tracing helpers.

Phase 2B of the enterprise-logging program. Exposes a ``/metrics`` endpoint
(auth via ``INTERNAL_SERVICE_KEY``) in Prometheus exposition format, so
customers can wire AI Identity into their existing Grafana stack without
us needing to build dashboard UI.

Metrics live in ``common.observability.metrics``. Both the API and Gateway
services import and increment the same collectors — each service exposes
its own ``/metrics`` endpoint which Prometheus scrapes independently.
"""
