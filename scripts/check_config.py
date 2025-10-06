#!/usr/bin/env python3
import os
import sys
from typing import Dict

# Load .env if present
try:
    from dotenv import load_dotenv
except Exception:
    print("⚠️ python-dotenv not installed; proceeding without .env loading")
    load_dotenv = None

if load_dotenv:
    # Load from project root
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print("✅ Loaded .env")
    else:
        print("⚠️ .env not found in project root; using current environment")

# Import project configuration
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from config.settings import get_config, validate_environment
except Exception as e:
    print(f"❌ Failed to import configuration: {e}")
    sys.exit(1)

REQUIRED_KEYS = [
    "SLACK_BOT_TOKEN",
    "SLACK_SIGNING_SECRET",
    "FINNHUB_API_KEY",
]
OPTIONAL_KEYS = [
    "SLACK_APP_TOKEN",
    "AWS_REGION",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "APPROVED_CHANNELS",
]


def mask(value: str, show: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= show:
        return "*" * len(value)
    return f"{'*' * (len(value) - show)}{value[-show:]}"


def collect_env(keys) -> Dict[str, str]:
    return {k: os.getenv(k, "") for k in keys}


def main() -> int:
    cfg = get_config()

    required = collect_env(REQUIRED_KEYS)
    optional = collect_env(OPTIONAL_KEYS)

    print("\n🔍 Configuration Check")
    print("=" * 60)
    print(f"App: {cfg.app_name} v{cfg.app_version}")
    print(f"Environment: {cfg.environment.value}")
    print(f"Debug Mode: {cfg.debug_mode}")

    # Required keys
    print("\nRequired keys:")
    missing = []
    for k, v in required.items():
        if v:
            print(f"  ✅ {k}: {mask(v)}")
        else:
            print(f"  ❌ {k}: MISSING")
            missing.append(k)

    # Optional keys
    print("\nOptional keys:")
    for k, v in optional.items():
        status = "✅" if v else "⚠️"
        display = mask(v) if v else "(not set)"
        print(f"  {status} {k}: {display}")

    # Use existing validator for deeper checks
    try:
        valid = validate_environment()
        print("\nValidator result:")
        if valid:
            print("  ✅ validate_environment(): PASSED")
        else:
            print("  ❌ validate_environment(): FAILED")
    except Exception as e:
        print(f"  ❌ validate_environment() raised error: {e}")

    # Exit code logic
    if missing:
        print("\nResult: ❌ Missing required keys → ", ", ".join(missing))
        return 1

    print("\nResult: ✅ All required keys present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
