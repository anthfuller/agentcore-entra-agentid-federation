# Troubleshooting

## `KeyError` containing a GUID or private value

**Cause:** A private identifier was used as an environment-variable name.

**Fix:** Use the literal names `ENTRA_TENANT_ID`, `ENTRA_BLUEPRINT_CLIENT_ID`, and `ENTRA_CHILD_AGENT_ID`, then read their values from `os.environ`.

## `AADSTS7002111` during Stage 2

**Possible validated cause:** The Blueprint ID was used where the child Agent Identity ID was required.

**Fix:** Verify that `ENTRA_CHILD_AGENT_ID` contains the actual child Agent Identity ID used by the validated relationship.

## `AccessDenied` for `GetWebIdentityToken`

Check:

- Runtime execution-role permission
- Audience `api://AzureADTokenExchange`
- Maximum assertion duration of 300 seconds
- `RS256` signing restriction
- Exact Runtime execution role used as the Federated Identity Credential subject

Do not substitute the AgentCore workload-identity ARN for the Runtime execution-role ARN.

## Runtime initialization timeout

A timeout can conceal a Python startup error. Inspect AgentCore Runtime or invocation logs for the actual traceback before changing federation, IAM, or timeout configuration.

## `IndentationError`

This is an application startup failure, not a Microsoft Entra federation failure. Run `py_compile` after every Python edit.

## `Error: null` or unusable controlled output

**Possible cause:** A streamed AgentCore entry point returned a plain dictionary instead of the expected streaming event envelope.

**Fix:** Preserve the event structure in the validated `main_federated.py`, which yields a `contentBlockDelta` event containing serialized sanitized output.

## Incorrect CLI prompt shape

The AgentCore CLI places supplied invocation text in the `prompt` field. The validated application recognizes the exact prompt `entra_graph_test` and also supports an action field with the same value in compatible harness payloads.
