"""Project-root conftest.

Sets dummy environment variables before pytest collects any tests so that
``app.config.Settings`` can instantiate at import time without real Feishu /
LLM credentials. Real values are only required at runtime in production.
"""

import os

_TEST_DEFAULTS = {
    "FEISHU_APP_ID": "test_app_id",
    "FEISHU_APP_SECRET": "test_app_secret",
    "FEISHU_VERIFY_TOKEN": "test_verify_token",
    "FEISHU_BITABLE_APP_TOKEN": "test_bitable_token",
    "FEISHU_TASK_TABLE_ID": "test_task_table",
    "FEISHU_PERSON_TABLE_ID": "test_person_table",
    "GITHUB_WEBHOOK_SECRET": "test_github_secret",
    "DEEPSEEK_KEY": "test_deepseek_key",
    "MATCH_MODE": "full",
}

for _key, _value in _TEST_DEFAULTS.items():
    os.environ.setdefault(_key, _value)
