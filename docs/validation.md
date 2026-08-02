# Validation Record

## Sanitized controlled-lab result

| Check | Result |
|---|---|
| Deployment | Successful |
| Runtime state | `READY` |
| Normal Strands and Bedrock invocation | Successful |
| Controlled federation request | Successful |
| Microsoft Graph HTTP status | `200` |
| Configured identity matched returned identity | `true` |
| Returned service-principal type | `ServiceIdentity` |
| Tokens logged | `false` |

## What the results prove

- The integrated AgentCore application remained functional for the tested normal invocation.
- Regional AWS STS produced an assertion that Microsoft Entra accepted for the configured Blueprint federation relationship.
- Blueprint token T1 acquisition succeeded.
- Child Agent Identity resource token TR acquisition succeeded for the requested Microsoft Graph scope.
- Microsoft Graph accepted TR and returned the configured service-principal record.
- The returned identity ID matched the configured child Agent Identity ID.
- The controlled response omitted token values.

## What the results do not prove

- Production readiness, resilience, scale, or comprehensive security hardening
- Agent 365 Connected Platforms synchronization or automatic registration
- Agent 365 SDK onboarding or Observability ingestion
- Microsoft Purview visibility, Conditional Access enforcement, or Defender protection
- Support commitments or endorsement by Microsoft or AWS
- That offline unit tests reproduce the live federation result
