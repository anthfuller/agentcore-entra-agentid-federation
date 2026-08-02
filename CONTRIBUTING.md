# Contributing

Contributions should keep the sample narrow, preserve the validated two-stage federation behavior, and avoid changing the ordinary Bedrock or MCP request path.

Before submitting a change:

1. Run Python syntax validation for every Python file.
2. Parse `pyproject.toml` and `config/agentcore.template.json`.
3. Run the offline unit tests.
4. Confirm no credentials, identifiers, ARNs, issuer URLs, tokens, authorization headers, customer data, private logs, or local paths are present.
5. Explain any behavior change explicitly.

Do not submit real tenant, application, object, account, runtime, role, or customer values. Do not include raw deployment logs.
