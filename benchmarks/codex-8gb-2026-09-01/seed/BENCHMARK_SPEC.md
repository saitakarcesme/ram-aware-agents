# Telemetry Lab benchmark fixture

Build a production-style TypeScript monorepo for ingesting, aggregating, serving, and visualizing synthetic telemetry.

## Required architecture

- `packages/shared`: validated event and aggregate schemas.
- `packages/generator`: deterministic sharded NDJSON generation with a CLI.
- `packages/analytics`: streaming ingestion, worker-thread aggregation, a CLI, and a repeatable benchmark command.
- `apps/dashboard`: Next.js App Router dashboard that reads generated aggregate artifacts, not the raw dataset.
- `tests/unit`, `tests/integration`, and Playwright end-to-end coverage.

## Dataset

The full workload contains 1,000,000 events split across 16 NDJSON shards. Events should include timestamp, service, region, status, latency, bytes, route, and trace identifiers. Generation must be deterministic from a seed.

## Operational requirements

- Avoid committing generated data.
- Commands must work from the repository root.
- Analytics must stream input rather than loading the complete dataset into one array.
- Persist compact JSON aggregates for the dashboard.
- Record benchmark duration, throughput, input bytes, and process memory.
- Keep implementations general-purpose and testable.
