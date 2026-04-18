#!/usr/bin/env python3
"""
IronVault Manufacturer Tool — Unlock Token Generator
Generates signed tokens to unlock bricked devices (authorized service center use only).

Usage:
  # Generate a 24-hour unlock token for a device
  python unlock_token_generator.py --device-id <UUID> --reason "authorized_repair" --valid-hours 24

  # For a batch of devices
  python unlock_token_generator.py --device-list devices.txt --reason "warranty_repair"
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone

import requests


def generate_unlock_token(device_id: str, device_secret: str, valid_hours: int = 24) -> dict:
    """
    Token = HMAC-SHA256(device_id + "|" + hour_floor, device_secret)
    Valid for `valid_hours` hours.
    The device side checks current and previous hour — so this generates
    a token for the current hour bucket, valid for up to valid_hours.
    """
    now = int(time.time()) // 3600  # Current hour bucket
    tokens = []
    for h in range(valid_hours):
        hour_bucket = now + h
        token = hmac.new(
            device_secret.encode(),
            f"{device_id}|{hour_bucket}".encode(),
            hashlib.sha256,
        ).hexdigest()
        tokens.append(token)

    return {
        "device_id": device_id,
        "primary_token": tokens[0],  # Token valid RIGHT NOW
        "all_tokens": tokens,        # All tokens for the validity window
        "valid_hours": valid_hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.fromtimestamp(
            (now + valid_hours) * 3600, tz=timezone.utc
        ).isoformat(),
    }


def get_device_secret_from_server(device_id: str, server: str, api_key: str) -> str:
    """Retrieve device secret from IronVault server (HTTPS only, requires admin key)."""
    resp = requests.get(
        f"{server}/api/admin/devices/{device_id}/secret",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["device_secret"]


def main():
    parser = argparse.ArgumentParser(description="IronVault Unlock Token Generator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--device-id", help="Single device UUID")
    group.add_argument("--device-list", help="File with one device UUID per line")

    parser.add_argument("--reason", required=True,
                        choices=["authorized_repair", "warranty_repair", "end_of_life",
                                 "employee_resigned", "admin_test"],
                        help="Reason for unlock")
    parser.add_argument("--valid-hours", type=int, default=24,
                        help="Token validity window in hours (default: 24)")
    parser.add_argument("--server", default="https://api.ironvault.com")
    parser.add_argument("--api-key", help="Admin API key (or IRONVAULT_API_KEY env var)")
    parser.add_argument("--output", help="Save tokens to JSON file")
    parser.add_argument("--device-secret", help="Provide device secret directly (testing only)")

    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("IRONVAULT_API_KEY", "")
    if not api_key and not args.device_secret:
        print("ERROR: --api-key or IRONVAULT_API_KEY required")
        sys.exit(1)

    device_ids = []
    if args.device_id:
        device_ids = [args.device_id]
    else:
        with open(args.device_list) as f:
            device_ids = [line.strip() for line in f if line.strip()]

    results = []
    for device_id in device_ids:
        print(f"\nGenerating unlock token for device: {device_id}")
        print(f"Reason: {args.reason}")

        try:
            if args.device_secret:
                secret = args.device_secret
            else:
                secret = get_device_secret_from_server(device_id, args.server, api_key)

            token_data = generate_unlock_token(device_id, secret, args.valid_hours)
            token_data["reason"] = args.reason

            print(f"✅ Token:       {token_data['primary_token']}")
            print(f"   Valid until: {token_data['expires_at']}")
            print(f"   Valid hours: {args.valid_hours}")

            results.append(token_data)

            # Log the unlock issuance to server
            if not args.device_secret:
                try:
                    requests.post(
                        f"{args.server}/api/admin/unlock-log",
                        json={
                            "device_id": device_id,
                            "reason": args.reason,
                            "valid_hours": args.valid_hours,
                            "generated_at": token_data["generated_at"],
                        },
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10,
                    )
                except Exception:
                    pass  # Non-critical logging failure

        except Exception as e:
            print(f"❌ Failed for {device_id}: {e}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Tokens saved to {args.output}")

    print(f"\n{'='*60}")
    print(f"Generated {len(results)} unlock token(s)")
    print(f"IMPORTANT: These tokens are time-limited and device-specific.")
    print(f"Do not share tokens. Log all unlock operations.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
