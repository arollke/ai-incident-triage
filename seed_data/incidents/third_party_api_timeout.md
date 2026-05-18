# Third Party API Timeout

## Summary

Shipping quotes were delayed because a third-party carrier API had intermittent timeouts.

## Timeline

- 16:11 UTC - Support reported delayed shipping quotes.
- 16:17 UTC - Engineers confirmed elevated timeout errors from the carrier API.
- 16:29 UTC - Timeout threshold and retry settings were adjusted.
- 16:43 UTC - Shipping quote latency returned to normal.

## Impact

Customers saw delayed shipping quotes during checkout, but orders could still be completed.

## Root Cause

The carrier API dependency returned intermittent timeout errors. Missing retry backoff caused requests to wait too long before failing over to cached quotes.

## Resolution

The team adjusted timeout and retry settings and verified cached quote fallback behavior.

## Follow-up Actions

- Add an alert for carrier API timeout rate.
- Document fallback behavior for shipping quote dependencies.
