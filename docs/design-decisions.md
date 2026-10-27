# Design Decisions and Scalability Notes

## Transaction management

Keep each current workflow inside one PostgreSQL transaction whenever possible. Appointment creation persists one appointment; consultation completion updates the consultation and appointment atomically; prescription creation is linked to a persisted consultation. Roll back on integrity failures and return a conflict rather than exposing SQL errors. Do not hold database transactions open while calling external services.

If a future workflow spans a payment provider, notifications and the database, use a durable state machine/outbox and idempotent consumers. Define compensating actions (for example, release a reserved slot if payment authorization fails) and reconciliation for uncertain outcomes. A distributed saga is not needed for the current single-database transaction.

## Idempotency and concurrency

The appointment endpoint accepts an optional Idempotency-Key. A replay with the same key and same patient/doctor/instant returns the original appointment; reuse for a different request conflicts. Clients should preserve the key across retries.

Current conflict detection compares exact scheduled instants. It does not enforce appointment duration, overlapping intervals, provider working hours, leave, holidays, or slot capacity. The row-lock approach must be verified against PostgreSQL under concurrent traffic; SQLite-based tests are not evidence of correct row-lock semantics. The next robust scheduling increment is a persisted availability-slot model with a unique/claim invariant enforced by PostgreSQL and a transaction that reserves one slot exactly once.

## Retry and backoff

- Retry transient reads with bounded exponential backoff plus random jitter.
- Retry writes only when they have a stable idempotency contract and the same key/payload is reused.
- Do not retry 400, 401, 403, 404, 409 or 422 automatically.
- For 429 and transient 502/503/504, respect Retry-After, cap attempts and cap total elapsed time.
- Retry a database transaction after a deadlock/serialization failure only after rollback and only at a well-defined transaction boundary.
- Avoid retry storms: apply jitter, concurrency caps, circuit breaking for external dependencies and retry budgets.

## Caching

Cache only public doctor search/profile responses if measurements show database pressure and the acceptable freshness window is documented. Invalidate on profile changes or use short TTLs. Do not cache private clinical records or authorization outcomes in a shared cache without strict identity/tenant keys, access checks and a defined invalidation policy. Cache outages must degrade to the database without bypassing authorization.

## Indexing and partitioning

Use EXPLAIN ANALYZE with representative data before adding indexes. Validate indexes for users.email, doctors.specialization, appointment patient/doctor/scheduled_at/status filters, consultation appointment uniqueness and prescription consultation lookup. Monitor write amplification and index size.

Do not partition prematurely. If audit events or appointments become large, evaluate time-based partitioning by event/creation date, retention windows and query locality. PostgreSQL uniqueness constraints on partitioned tables can require the partition key, so partition design must be tested against idempotency and foreign-key invariants before adoption. Keep migration and rollback strategy documented.

## Async jobs and analytics

Notifications, reminders, exports and aggregate reporting should move to a durable queue/worker when they exceed request latency budgets. Use an outbox if a committed booking must reliably trigger an asynchronous event. Admin analytics should use authorized aggregate queries or maintained summaries, avoid returning identifiable clinical details by default, and never run unbounded full-table scans in latency-sensitive requests.

## SLO and capacity validation

The assignment target of 100,000 consultations/day is an average of about 1.16 consultations per second; peak traffic and reads/writes will be higher and must be measured. Establish representative test data, traffic shape and concurrency, then record throughput, p50/p95/p99 latency, error rate, DB pool wait, CPU and memory. The provided k6 script is only a liveness smoke test. It does not validate write latency or consultation capacity.

## Backup and disaster recovery

Use encrypted managed backups and point-in-time recovery where supported. Keep backup access separate from app credentials; alert on backup failure and record retention. Restore into an isolated environment on a schedule and measure recovery point/time. Proposed planning objectives are RPO <= 15 minutes and RTO <= 4 hours; these are not guarantees until tested. Never test restoration over the only production copy.
