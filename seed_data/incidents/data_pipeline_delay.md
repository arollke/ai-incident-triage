# Data Pipeline Delay

## Summary

Daily analytics dashboards were delayed after the reporting pipeline retried a failed batch.

## Timeline

- 02:05 UTC - Batch job failed during warehouse export.
- 02:18 UTC - Retry started automatically.
- 03:06 UTC - Export completed.
- 03:24 UTC - Dashboards refreshed with current data.

## Impact

Internal teams saw stale analytics dashboards for 79 minutes. No customer-facing systems were impacted.

## Root Cause

The reporting pipeline failed because a warehouse export dependency timed out. The retry process completed successfully but delayed dashboard freshness.

## Resolution

The team allowed the retry to complete and verified dashboard data freshness after the export finished.

## Follow-up Actions

- Add an alert for reporting pipeline export duration.
- Document the retry process for warehouse export delays.
