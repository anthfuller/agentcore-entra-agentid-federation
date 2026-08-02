from __future__ import annotations

import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "app" / "layeredobsagent" / "entra_token_provider.py"


def _load_module():
    botocore = types.ModuleType("botocore")
    exceptions = types.ModuleType("botocore.exceptions")
    session = types.ModuleType("botocore.session")

    class BotoCoreError(Exception):
        pass

    class ClientError(Exception):
        pass

    exceptions.BotoCoreError = BotoCoreError
    exceptions.ClientError = ClientError
    session.get_session = mock.Mock()
    botocore.exceptions = exceptions
    botocore.session = session

    with mock.patch.dict(sys.modules, {
        "botocore": botocore,
        "botocore.exceptions": exceptions,
        "botocore.session": session,
    }):
        spec = importlib.util.spec_from_file_location("entra_token_provider_test", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


class TokenProviderErrorTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_module()

    def test_empty_resource_scope_is_sanitized(self):
        result = self.module.get_resource_token("   ")
        self.assertFalse(result.success)
        self.assertIsNone(result.access_token)
        self.assertEqual(result.error["stage"], "Input validation")
        self.assertNotIn("access_token", result.error)

    def test_missing_environment_variable_is_sanitized(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            result = self.module.get_resource_token("https://graph.microsoft.com/.default")
        self.assertFalse(result.success)
        self.assertIsNone(result.access_token)
        self.assertEqual(result.error["stage"], "Configuration")
        self.assertEqual(
            result.error["description"],
            "Required environment variable is missing: ENTRA_TENANT_ID",
        )
        serialized = repr(result)
        self.assertNotIn("Bearer ", serialized)
        self.assertNotIn("Authorization", serialized)


if __name__ == "__main__":
    unittest.main()
