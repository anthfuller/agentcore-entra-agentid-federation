# Safe Rollback

1. Preserve a private copy of the integrated root-level `agentcore.json` and the validated federated source before replacement.
2. Restore the last known-good private configuration or select the original `main.py` entry point in a private rollback configuration.
3. Keep the CodeZip location consistent with the restored entry point.
4. Run Python syntax validation.
5. Run `agentcore deploy --dry-run` and review the plan.
6. Run `agentcore deploy`.
7. Run `agentcore status` and confirm `READY`.
8. Invoke a normal application prompt and verify the baseline behavior.

Rollback should not default to deleting working identity resources, Federated Identity Credentials, isolated probe files, or evidence needed to understand the validated state. Destructive cleanup should be a separately reviewed action.
