# Payment Outage

## Summary

Checkout payments were unavailable for customers in the US region for 42 minutes on Saturday morning.

## Timeline

- 09:02 UTC - Alert fired for elevated payment authorization failures.
- 09:07 UTC - On-call engineer confirmed checkout payment attempts were failing.
- 09:19 UTC - Payment gateway connection pool saturation identified.
- 09:34 UTC - Connection pool configuration rolled back.
- 09:44 UTC - Payment authorization success rate returned to normal.

## Impact

Customers in the US region could not complete card payments during the incident. Approximately 18% of checkout attempts failed.

## Root Cause

A deployment changed the payment gateway connection pool limit from 100 to 20. The lower limit exhausted available connections during normal Saturday traffic and caused payment authorization requests to fail.

## Resolution

The team rolled back the connection pool configuration and verified payment authorization success rates recovered.

## Follow-up Actions

- Add a pre-deploy configuration check for payment gateway pool limits.
- Add an alert for connection pool saturation before customer-facing failures occur.
- Document the rollback procedure for payment gateway configuration changes.
