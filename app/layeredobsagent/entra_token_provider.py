"""Reusable Microsoft Entra Agent ID token provider for AgentCore.

Implements the validated two-stage autonomous-agent exchange:
AWS signed assertion -> Blueprint token (T1) -> child Agent Identity resource token (TR).
Sensitive token values remain in memory and are never logged by this module.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

import botocore.exceptions
import botocore.session

TOKEN_EXCHANGE_AUDIENCE = "api://AzureADTokenExchange"
CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
HTTP_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class TokenResult:
    success: bool
    access_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    resource_scope: str | None = None
    error: dict[str, Any] | None = None


def _sanitized_http_error(stage: str, exc: urllib.error.HTTPError) -> dict[str, Any]:
    microsoft_error_code = None
    description = "Microsoft Entra token request failed"
    correlation_id = None
    timestamp = None

    try:
        parsed = json.loads(exc.read().decode("utf-8", errors="replace"))
        microsoft_error_code = parsed.get("error")
        description = parsed.get("error_description") or description
        correlation_id = parsed.get("correlation_id")
        timestamp = parsed.get("timestamp")
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass

    return {
        "stage": stage,
        "http_status": exc.code,
        "microsoft_error_code": microsoft_error_code,
        "description": description,
        "correlation_id": correlation_id,
        "timestamp": timestamp,
    }


def _post_token_request(token_endpoint: str, form_data: dict[str, str]) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        token_endpoint,
        data=urllib.parse.urlencode(form_data).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def get_resource_token(resource_scope: str) -> TokenResult:
    """Acquire a child Agent Identity token for an explicit downstream scope.

    The returned access token is intended only for in-process use by the caller.
    The caller must not print, log, trace, serialize, or return it in an agent response.
    """
    if not isinstance(resource_scope, str) or not resource_scope.strip():
        return TokenResult(
            success=False,
            resource_scope=resource_scope if isinstance(resource_scope, str) else None,
            error={
                "stage": "Input validation",
                "http_status": None,
                "microsoft_error_code": None,
                "description": "resource_scope must be a non-empty string",
                "correlation_id": None,
                "timestamp": None,
            },
        )

    stage = "Configuration"
    try:
        tenant_id = os.environ["ENTRA_TENANT_ID"]
        blueprint_client_id = os.environ["ENTRA_BLUEPRINT_CLIENT_ID"]
        child_agent_id = os.environ["ENTRA_CHILD_AGENT_ID"]
        region = os.getenv("AWS_REGION", "us-east-1")
        token_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

        stage = "AWS signed assertion"
        sts = botocore.session.get_session().create_client("sts", region_name=region)
        aws_assertion = sts.get_web_identity_token(
            Audience=[TOKEN_EXCHANGE_AUDIENCE],
            DurationSeconds=300,
            SigningAlgorithm="RS256",
        )["WebIdentityToken"]

        stage = "Blueprint token exchange"
        _, t1_result = _post_token_request(
            token_endpoint,
            {
                "client_id": blueprint_client_id,
                "grant_type": "client_credentials",
                "scope": f"{TOKEN_EXCHANGE_AUDIENCE}/.default",
                "client_assertion_type": CLIENT_ASSERTION_TYPE,
                "client_assertion": aws_assertion,
                "fmi_path": child_agent_id,
            },
        )
        t1 = t1_result["access_token"]

        stage = "Child Agent Identity resource token exchange"
        _, tr_result = _post_token_request(
            token_endpoint,
            {
                "client_id": child_agent_id,
                "grant_type": "client_credentials",
                "scope": resource_scope,
                "client_assertion_type": CLIENT_ASSERTION_TYPE,
                "client_assertion": t1,
            },
        )
        tr = tr_result["access_token"]

        return TokenResult(
            success=True,
            access_token=tr,
            token_type=tr_result.get("token_type"),
            expires_in=tr_result.get("expires_in"),
            resource_scope=resource_scope,
        )

    except urllib.error.HTTPError as exc:
        return TokenResult(
            success=False,
            resource_scope=resource_scope,
            error=_sanitized_http_error(stage, exc),
        )
    except urllib.error.URLError as exc:
        return TokenResult(
            success=False,
            resource_scope=resource_scope,
            error={
                "stage": stage,
                "http_status": None,
                "microsoft_error_code": None,
                "description": f"Network error: {exc.reason}",
                "correlation_id": None,
                "timestamp": None,
            },
        )
    except KeyError as exc:
        missing_name = str(exc).strip("'")
        description = (
            f"Required environment variable is missing: {missing_name}"
            if missing_name.startswith("ENTRA_")
            else "Required token response field was missing"
        )
        return TokenResult(
            success=False,
            resource_scope=resource_scope,
            error={
                "stage": stage,
                "http_status": None,
                "microsoft_error_code": None,
                "description": description,
                "correlation_id": None,
                "timestamp": None,
            },
        )
    except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as exc:
        return TokenResult(
            success=False,
            resource_scope=resource_scope,
            error={
                "stage": stage,
                "http_status": None,
                "microsoft_error_code": None,
                "description": f"AWS STS request failed: {type(exc).__name__}",
                "correlation_id": None,
                "timestamp": None,
            },
        )
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
        return TokenResult(
            success=False,
            resource_scope=resource_scope,
            error={
                "stage": stage,
                "http_status": None,
                "microsoft_error_code": None,
                "description": "Token endpoint returned an invalid response",
                "correlation_id": None,
                "timestamp": None,
            },
        )
