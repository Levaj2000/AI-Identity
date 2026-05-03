"""Eval harness for Ada — citation verification gate.

The rules of evidence in `agent/ada/agent.py` are load-bearing — citation
discipline regresses silently on any prompt edit or model swap. This
package provides a pure-function citation verifier (no ADK / Vertex
dependency) plus a small bundled golden set, run on every PR that
touches `agent/`.
"""
