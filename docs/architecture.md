# Validated Architecture

## Flow

1. The Amazon Bedrock AgentCore application runs under its Runtime execution role.
2. A regional AWS STS client issues a short-lived, RS256-signed workload assertion for audience `api://AzureADTokenExchange`, with a maximum duration of 300 seconds.
3. Microsoft Entra validates the AWS issuer, exact Runtime execution-role subject, and audience through the Agent Identity Blueprint Federated Identity Credential.
4. The application submits the AWS assertion to the tenant token endpoint using the Blueprint App ID and the validated child identity relationship in `fmi_path`, acquiring Blueprint token T1.
5. The application uses T1 as the client assertion for the child Agent Identity.
6. Microsoft Entra issues resource token TR for the explicitly requested downstream resource scope.
7. The application uses TR only in process for a read-only Microsoft Graph request to `https://graph.microsoft.com/v1.0/servicePrincipals/{child_agent_id}`.
8. The controlled AgentCore response returns only sanitized status, identity-match, service-principal-type, and error information.

## Isolation from ordinary requests

The token provider is called only by the explicit `entra_graph_test` path or by code that deliberately requests an Entra-protected resource token. Normal Strands, Amazon Bedrock, MCP, session, cache, prompt, message, tool-result, and streaming behavior remains on the existing application path.

## Token handling

The AWS assertion, T1, and TR exist only in process memory. The controlled response does not include them. The application sends TR in the Microsoft Graph `Authorization` header but does not return that header or value.
