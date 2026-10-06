# Metric definitions, schema version 1

- Throughput: first unique qualifying parent deliveries in [warmup,T) / (T-warmup).
  Offered requests may precede warmup. All arrivals and terminal statuses retain
  full-run accounting. Pair yield is full-run completed parents / offered parents.
- Queue wait: sum of waits for the winning child's forwarding servers, excludes
  service/purification/deferral. Node sojourn: queue wait + service at that node.
  Reserved-path sojourn: all time from winning reservation to delivery, includes
  purification. End-to-end latency: arrival to first delivery, includes deferral.
- Latency cohort: arrivals >=warmup that complete before T. Dropped and unfinished
  requests are excluded from delay CDFs but not throughput or conservation tables.
  Short completed latencies can result from selection and right-censoring.
- `mean_queue`: time integral of classical waiting jobs / measurement duration.
  `mean_system`: integral of waiting+serving jobs; `utilization`: server-busy integral.
  `mean_qubits`: held endpoint slots. `peak_qubits` is full-run maximum.
- `time_full_fraction`: node time with all slots occupied / measurement duration.
  `memory_blocking`: failed atomic reservation attempts / all reservation attempts,
  includes repeated deferrals and children. This is not offered-parent blocking or
  M/M/1/K P_full. `drops_by_cause` and request rows allow parent rejection fractions.
- Fidelity distribution: qualifying delivered proxy values, with below-threshold
  attempt count separate. Path estimates include literal Eq. (5), chain-aging value,
  planned rounds, probabilities, and individual constraint checks at each decision.
- Request terminal counts partition full-run offers. Admitted and deferred overlap;
  they are intermediate, not terminal partitions. Attempt resource-work totals can
  exceed winning parent service; use attempts.parquet for actual replication work.
- Interrupted services record completed work only in service_time; active partial
  service still contributes to utilization integrals. This censoring is intentional.
- Independent-run CIs use Student-t across seeds; undefined run metrics omit that
  replicate and report n. One replicate has no CI. Correlated per-event data are
  never used as independent replications. Topology seed is retained in every row.

`io.schemas` defines empty-table-compatible Arrow fields. `node_metrics` has one
row per node even for no traffic. `types.Result` and manifests carry schema_version=1.
Raw events are optional; disabling them leaves all scientific simulation choices
and RNG consumption unchanged. Path decisions remain available even with trace off.
