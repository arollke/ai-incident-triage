# Failed Deploy Rollback

## Summary

Profile updates were degraded for customers after a failed deployment rollback.

## Timeline

- 14:03 UTC - Deployment completed for the profile service.
- 14:09 UTC - Error rate alert fired for profile update requests.
- 14:18 UTC - Team attempted rollback and saw the same errors.
- 14:31 UTC - Feature flag routing was restored.
- 14:38 UTC - Profile update error rate returned to normal.

## Impact

Customers could not reliably save profile changes for 29 minutes. Approximately 9% of profile update requests failed.

## Root Cause

A deployment changed feature flag routing for the profile service. The rollback procedure was missing a step to restore the previous flag configuration and caused continued request failures.

## Resolution

The team restored the previous feature flag configuration and verified successful profile updates.

## Follow-up Actions

- Add a pre-deploy validation check for profile feature flag routing.
- Document the rollback procedure for profile service releases.
