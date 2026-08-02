from typing import Any
from collections import OrderedDict
from strands import Agent, tool
import asyncio
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client
from entra_token_provider import get_resource_token
import json
import urllib.error
import urllib.request
import os

app = BedrockAgentCoreApp()
log = app.logger

# Define a Streamable HTTP MCP Client
mcp_clients = [get_streamable_http_mcp_client()]

DEFAULT_SYSTEM_PROMPT = """
You are a helpful assistant. Use tools when appropriate.

"""

MICROSOFT_GRAPH_SCOPE = "https://graph.microsoft.com/.default"

# Define a collection of tools used by the model
tools = []

_INLINE_FUNCTION_NAMES = set()

# Define a simple function tool
@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers"""
    return a+b
tools.append(add_numbers)



# Add MCP client to tools if available
for mcp_client in mcp_clients:
    if mcp_client:
        tools.append(mcp_client)


def _make_conversation_manager():
    return NullConversationManager()

# Reuses one Agent per session_id so each session keeps its own in-process
# conversation history (best-effort; resets on cold start). The cache is bounded
# to 128 sessions with LRU eviction (least-recently-used is dropped and its
# history reset) so a single process serving many sessions cannot leak history
# between them or grow without limit. For durable history, attach a session manager.
def agent_factory():
    cache = OrderedDict()
    def get_or_create_agent(session_id):
        if session_id in cache:
            cache.move_to_end(session_id)
            return cache[session_id]
        if len(cache) >= 128:
            cache.popitem(last=False)
        cache[session_id] = Agent(
            model=load_model(),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            tools=tools,
            conversation_manager=_make_conversation_manager(),
            hooks=[
            ],
        )
        return cache[session_id]
    return get_or_create_agent
get_or_create_agent = agent_factory()


def _extract_prompt(payload: dict):
    """Accept harness-style messages[], tool_results[], or plain prompt string payloads."""
    if "messages" in payload:
        return payload["messages"]
    if "tool_results" in payload:
        return [{"role": "user", "content": [{"toolResult": {
            "toolUseId": tr["toolUseId"],
            "status": tr.get("status", "success"),
            "content": tr.get("content", []),
        }} for tr in payload["tool_results"]]}]
    return payload.get("prompt", "")


def _has_inline_function_call(messages) -> bool:
    """Return True if messages contains an assistant toolUse for an inline function tool."""
    if not _INLINE_FUNCTION_NAMES or not isinstance(messages, list):
        return False
    for msg in messages:
        if msg.get("role") == "assistant":
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("toolUse", {}).get("name") in _INLINE_FUNCTION_NAMES:
                    return True
    return False


def _is_inline_function_call(event: dict) -> bool:
    """Check if a contentBlockStart event is for an inline function tool."""
    if not _INLINE_FUNCTION_NAMES:
        return False
    cbs = event.get("contentBlockStart", {})
    start = cbs.get("start", {})
    tool_use = start.get("toolUse") if isinstance(start, dict) else None
    return tool_use is not None and tool_use.get("name") in _INLINE_FUNCTION_NAMES



def run_controlled_graph_test():
    stage = "Microsoft Graph service principal lookup"
    tokens_logged = False

    try:
        child_agent_id = os.environ["ENTRA_CHILD_AGENT_ID"]
        token_result = get_resource_token(MICROSOFT_GRAPH_SCOPE)
        if not token_result.success or not token_result.access_token:
            return {
                "stage": stage,
                "success": False,
                "http_status": None,
                "identity_id_match": False,
                "service_principal_type": None,
                "error": token_result.error or {
                    "description": "Microsoft Graph resource token acquisition failed"
                },
                "tokens_logged": tokens_logged,
            }

        request = urllib.request.Request(
            f"https://graph.microsoft.com/v1.0/servicePrincipals/{child_agent_id}",
            method="GET",
            headers={"Authorization": f"Bearer {token_result.access_token}"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            return {
                "stage": stage,
                "success": 200 <= response.status < 300,
                "http_status": response.status,
                "identity_id_match": response_data.get("id") == child_agent_id,
                "service_principal_type": response_data.get("servicePrincipalType"),
                "error": None,
                "tokens_logged": tokens_logged,
            }
    except urllib.error.HTTPError as exc:
        return {
            "stage": stage,
            "success": False,
            "http_status": exc.code,
            "identity_id_match": False,
            "service_principal_type": None,
            "error": {"description": "Microsoft Graph request failed"},
            "tokens_logged": tokens_logged,
        }
    except urllib.error.URLError as exc:
        return {
            "stage": stage,
            "success": False,
            "http_status": None,
            "identity_id_match": False,
            "service_principal_type": None,
            "error": {"description": "Microsoft Graph network request failed"},
            "tokens_logged": tokens_logged,
        }
    except KeyError as exc:
        missing_name = str(exc).strip("'")
        return {
            "stage": stage,
            "success": False,
            "http_status": None,
            "identity_id_match": False,
            "service_principal_type": None,
            "error": {
                "description": f"Required environment variable is missing: {missing_name}"
            },
            "tokens_logged": tokens_logged,
        }
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
        return {
            "stage": stage,
            "success": False,
            "http_status": None,
            "identity_id_match": False,
            "service_principal_type": None,
            "error": {"description": "Microsoft Graph returned an invalid response"},
            "tokens_logged": tokens_logged,
        }


@app.entrypoint
async def invoke(payload, context):
    if isinstance(payload, dict) and (
        payload.get("action") == "entra_graph_test"
        or payload.get("prompt") == "entra_graph_test"
    ):
        yield {
            "event": {
                "contentBlockDelta": {
                    "delta": {
                        "text": json.dumps(run_controlled_graph_test())
                    }
                }
            }
        }
        return

    log.info("Invoking Agent.....")


    session_id = getattr(context, 'session_id', 'default-session')
    agent = get_or_create_agent(session_id)

    prompt = _extract_prompt(payload)


    async for event in agent.stream_async(
        prompt,
    ):
        if not isinstance(event, dict) or "event" not in event:
            continue
        cbs = event["event"].get("contentBlockStart")
        if cbs is not None and not cbs.get("start"):
            continue
        yield event


if __name__ == "__main__":
    app.run()
