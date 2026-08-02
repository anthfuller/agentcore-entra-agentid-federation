# Amazon Bedrock AgentCore to Microsoft Entra Agent ID Federation

## Status

Validated proof of concept from a controlled lab environment. The active AgentCore entry point is `app/layeredobsagent/main_federated.py`. The unchanged `main.py` file is retained only as the pre-federation application baseline and is not configured for deployment.

## What this sample demonstrates

This repository demonstrates passwordless, two-stage federation from an Amazon Bedrock AgentCore Runtime application to Microsoft Entra Agent ID, followed by a controlled, read-only Microsoft Graph service-principal lookup.

The federation path is invoked only by the explicit `entra_graph_test` request. Ordinary Strands, Amazon Bedrock, and MCP requests do not acquire a Microsoft Graph token.

## Validated architecture

```text
AgentCore Runtime execution role
  -> regional AWS STS GetWebIdentityToken
  -> AWS-signed workload assertion
  -> Microsoft Entra Blueprint token (T1)
  -> child Agent Identity resource token (TR)
  -> Microsoft Graph service-principal GET
  -> sanitized HTTP 200 validation response
```

See [Architecture](docs/architecture.md).

## Validated result

- Runtime status: `READY`
- Normal Strands and Amazon Bedrock invocation succeeded
- Controlled Microsoft Graph request returned HTTP `200`
- `identity_id_match`: `true`
- `service_principal_type`: `ServiceIdentity`
- `tokens_logged`: `false`
- No Microsoft client secret was used in the tested path
- No AWS assertion, T1, or TR value was returned in the controlled response

## Repository layout

```text
app/layeredobsagent/          Validated CodeZip application directory
  main_federated.py           Active AgentCore entry point
  entra_token_provider.py     Passwordless two-stage token provider
  main.py                     Unchanged pre-federation baseline
  model/load.py               Bedrock model loader
  mcp_client/client.py        Streamable HTTP MCP client
config/agentcore.template.json Sanitized AgentCore configuration template
docs/                         Architecture, deployment, validation, and boundaries
tests/                        Offline tests; no live AWS or Microsoft calls
```

## Prerequisites

- Python compatible with the project metadata and the configured AgentCore runtime
- Amazon Bedrock AgentCore CLI and authenticated AWS access for deployment
- An AgentCore Runtime execution role permitted to call regional AWS STS `GetWebIdentityToken`
- A Microsoft Entra Agent Identity Blueprint with a Federated Identity Credential
- An existing child Agent Identity associated through the validated `fmi_path` relationship
- Microsoft Graph application permission sufficient for the controlled service-principal lookup, with required consent

## Critical identifier mapping

| Setting | Required value | Must not be confused with |
|---|---|---|
| `ENTRA_TENANT_ID` | Microsoft Entra tenant ID | A public or committed value |
| `ENTRA_BLUEPRINT_CLIENT_ID` | Blueprint **App ID** | Blueprint service-principal object ID or child identity ID |
| `ENTRA_CHILD_AGENT_ID` | Existing child Agent Identity ID/object ID used by the validated relationship | Blueprint ID, Agent 365 registration ID, AgentCore workload-identity ARN, or Runtime execution-role ARN |
| FIC subject | Exact AgentCore Runtime execution-role ARN | AgentCore workload-identity ARN |
| FIC audience | `api://AzureADTokenExchange` | A Microsoft Graph scope |

The validated AWS assertion uses audience `api://AzureADTokenExchange`, maximum duration `300` seconds, and signing algorithm `RS256`.

## AWS trust prerequisites

The Runtime execution role must be the exact subject configured in the Blueprint Federated Identity Credential. It must be authorized to obtain the regional AWS-signed assertion with the validated audience, duration, and signing algorithm restrictions.

Do not commit the execution-role ARN, AWS account ID, issuer URL, or any AWS credential.

## Microsoft Entra prerequisites

Configure the Blueprint Federated Identity Credential with:

- Subject: exact AgentCore Runtime execution-role ARN
- Audience: `api://AzureADTokenExchange`
- Issuer: the correct AWS outbound federation issuer for the validated environment

The Blueprint App ID is used for Stage 1. The child Agent Identity ID is supplied as `fmi_path` in Stage 1 and as `client_id` in Stage 2.

## Configuration

1. Copy `config/agentcore.template.json` to a private root-level `agentcore.json`.
2. Replace placeholders with private deployment values.
3. Supply `ENTRA_TENANT_ID`, `ENTRA_BLUEPRINT_CLIENT_ID`, `ENTRA_CHILD_AGENT_ID`, and `AWS_REGION` through AgentCore Runtime environment configuration or the intended deployment mechanism.

`.env.template` documents required names only. The application does **not** automatically load a dotenv file.

The validated CodeZip layout requires commands to be run from the repository root, where `agentcore.json` can reference `app/layeredobsagent/` and the entry point `main_federated.py`.

## Local validation

```powershell
python -m py_compile app/layeredobsagent/main_federated.py app/layeredobsagent/entra_token_provider.py app/layeredobsagent/main.py app/layeredobsagent/model/load.py app/layeredobsagent/mcp_client/client.py
python -m unittest discover -s tests -v
```

These checks are offline and do not prove live federation.

## AgentCore dry run

From the repository root, with a private root-level `agentcore.json` in place:

```powershell
agentcore deploy --dry-run
```

## Deployment

```powershell
agentcore deploy
agentcore status
```

Confirm that the Runtime reaches `READY` before invocation.

## Normal application validation

```powershell
agentcore invoke "What is 2 plus 2?"
```

This exercises the normal Strands and Amazon Bedrock path and should not request a Microsoft Graph token.

## Controlled federation validation

```powershell
agentcore invoke "entra_graph_test"
```

The AgentCore CLI places the supplied invocation text in the `prompt` field. The active entry point also accepts `{"action":"entra_graph_test"}` when invoked through a compatible harness.

## Expected sanitized output

A successful controlled response has the following shape and contains no token values:

```json
{
  "stage": "Microsoft Graph service principal lookup",
  "success": true,
  "http_status": 200,
  "identity_id_match": true,
  "service_principal_type": "ServiceIdentity",
  "error": null,
  "tokens_logged": false
}
```

## Security considerations

- Tokens remain in process memory and must not be logged, traced, serialized, or returned.
- The Microsoft Graph token is acquired only for an explicit Entra-protected resource request.
- Keep the active `agentcore.json`, tenant values, IDs, account details, role ARNs, issuer URLs, and logs private.
- The sample uses a public network mode because that is the supplied validated configuration; assess network controls independently before broader use.
- Review external MCP endpoint use and data handling for your environment.

See [Security Policy](SECURITY.md).

## Troubleshooting

See [Troubleshooting](docs/troubleshooting.md) for verified reusable failure patterns.

## Rollback

See [Rollback](docs/rollback.md). The default rollback preserves known-good configuration and identity resources rather than deleting them.

## Claims boundary

See [Claims Boundary](docs/claims-boundary.md) for the exact scope of validation and explicit non-claims.

## Disclaimer

This proof of concept was developed and validated in a controlled lab environment. It is not an official Microsoft or AWS reference architecture, product commitment, or production deployment guide. Review and test all code in a non-production environment before use.

## References

- [Architecture](docs/architecture.md)
- [Deployment](docs/deployment.md)
- [Validation](docs/validation.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Rollback](docs/rollback.md)
- [Claims Boundary](docs/claims-boundary.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
