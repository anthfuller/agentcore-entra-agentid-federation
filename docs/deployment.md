# Deployment

## Prerequisites

- Authenticated AWS environment and Amazon Bedrock AgentCore CLI
- Required Amazon Bedrock model access
- Runtime execution-role permission for regional AWS STS `GetWebIdentityToken`
- Microsoft Entra Blueprint Federated Identity Credential whose subject is the exact Runtime execution-role ARN and whose audience is `api://AzureADTokenExchange`
- Blueprint App ID, child Agent Identity ID, and tenant ID
- Required Microsoft Graph permission and consent for the controlled lookup

## Required project layout

The validated AgentCore configuration uses:

- `build`: `CodeZip`
- `codeLocation`: `app/layeredobsagent/`
- `entrypoint`: `main_federated.py`
- `runtimeVersion`: `PYTHON_3_14`

Run AgentCore commands from the repository root.

## Private environment configuration

Copy `config/agentcore.template.json` to a private root-level `agentcore.json`, then replace placeholders. Do not commit the resulting file.

Required variables:

```text
ENTRA_TENANT_ID
ENTRA_BLUEPRINT_CLIENT_ID
ENTRA_CHILD_AGENT_ID
AWS_REGION
```

The code defaults `AWS_REGION` to `us-east-1` when it is absent. It does not automatically load `.env`.

## Syntax validation

```powershell
python -m py_compile app/layeredobsagent/main_federated.py app/layeredobsagent/entra_token_provider.py app/layeredobsagent/main.py app/layeredobsagent/model/load.py app/layeredobsagent/mcp_client/client.py
```

## JSON and TOML validation

```powershell
python -c "import json; json.load(open('config/agentcore.template.json', encoding='utf-8')); print('JSON OK')"
python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('TOML OK')"
```

## AgentCore dry run

```powershell
agentcore deploy --dry-run
```

Review the generated plan and confirm the CodeZip source and active entry point.

## Deployment and READY check

```powershell
agentcore deploy
agentcore status
```

Do not invoke until the Runtime reports `READY`.

## Normal application invocation

```powershell
agentcore invoke "What is 2 plus 2?"
```

This validates the normal application path without intentionally acquiring a Microsoft Graph token.

## Controlled federation invocation

```powershell
agentcore invoke "entra_graph_test"
```

Expect a streamed AgentCore event containing a serialized, sanitized result. No AWS assertion, T1, TR, bearer value, or authorization header should appear.
