---
title: Loan enforcement thresholds
audience: internal
source_decisions: [D906]
implementation_status: built
rag_index: never
public_rag_safe: false
last_updated: 2026-09-03
---

# Loan enforcement thresholds

This document is SYNTHETIC and, like every tier-internal document, is NEVER
ingested: `rag_index: never` and `audience: internal` each independently abort
the ingestion run before a row is written. It exists in this package precisely
so the tests can prove that — a corpus with no internal document could not
demonstrate that internal documents stay out.

Its content is deliberately the kind of thing that must not leak: the tuned
numbers behind an enforcement rule.

## Thresholds

Placeholder values, invented for this package. TUNED_LATE_RETURN_LIMIT late
returns inside TUNED_WINDOW_DAYS days triggers a review. The reservation
ceiling drops to TUNED_REDUCED_CEILING for TUNED_PENALTY_DAYS days.
