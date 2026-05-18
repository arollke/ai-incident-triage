# Monitoring Gap

## Summary

Invoice email delivery was delayed and the team was not alerted automatically.

## Timeline

- 07:20 UTC - Customer support reported missing invoice emails.
- 07:31 UTC - Engineers found a delivery queue backlog.
- 07:42 UTC - Workers were restarted.
- 08:05 UTC - Email delivery backlog cleared.

## Impact

Customers received invoice emails late, but invoice data remained available in the account dashboard.

## Root Cause

The delivery queue alert was missing for the invoice email worker. The monitoring gap delayed detection until customer support escalated the issue.

## Resolution

The team restarted the email workers and confirmed the invoice delivery queue drained.

## Follow-up Actions

- Add an alert for invoice email queue age.
- Review monitoring coverage for customer notification workers.
