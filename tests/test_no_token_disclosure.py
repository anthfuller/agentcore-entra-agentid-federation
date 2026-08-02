from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMITTED_TEXT_FILES = [
    path for path in ROOT.rglob("*")
    if path.is_file() and ".git" not in path.parts and path.suffix not in {".pyc", ".zip"}
]

FORBIDDEN_PRIVATE_PATTERNS = {
    "GUID": re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b"),
    "AWS account ID": re.compile(r"(?<!\d)\d{12}(?!\d)"),
    "ARN": re.compile(r"\barn:(?:aws|aws-us-gov|aws-cn):[^\s\"']+"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Bearer value": re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    "JWT-like value": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "literal tenant token URL": re.compile(r"https://login\.microsoftonline\.com/[0-9a-fA-F-]{36}/"),
    "Windows user path": re.compile(r"(?i)\bC:\\Users\\[^\\\s]+"),
}


class NoTokenDisclosureTests(unittest.TestCase):
    def test_controlled_success_shape_has_no_token_fields(self):
        record = {
            "stage": "Microsoft Graph service principal lookup",
            "success": True,
            "http_status": 200,
            "identity_id_match": True,
            "service_principal_type": "ServiceIdentity",
            "error": None,
            "tokens_logged": False,
        }
        serialized = json.dumps(record)
        for forbidden in (
            "access_token", "aws_assertion", '"t1"', '"tr"',
            "Authorization", "Bearer ", "client_assertion",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_committed_files_contain_no_private_identifier_patterns(self):
        findings = []
        for path in COMMITTED_TEXT_FILES:
            text = path.read_text(encoding="utf-8", errors="replace")
            for label, pattern in FORBIDDEN_PRIVATE_PATTERNS.items():
                for match in pattern.finditer(text):
                    findings.append(f"{path.relative_to(ROOT)}: {label}: {match.group(0)}")
        self.assertEqual(findings, [], "\n".join(findings))

    def test_active_private_agentcore_file_is_not_committed(self):
        self.assertFalse((ROOT / "agentcore.json").exists())
        self.assertTrue((ROOT / "config" / "agentcore.template.json").exists())


if __name__ == "__main__":
    unittest.main()
