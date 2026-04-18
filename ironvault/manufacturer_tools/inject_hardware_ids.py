#!/usr/bin/env python3
"""
IronVault Manufacturer Tool — Hardware ID Injector
Registers a device's golden hardware fingerprint during manufacturing.
Run this ONCE per device before shipping.

Usage:
  python inject_hardware_ids.py --device-serial ABC123 --imei 490154203237518 \\
    --model "Galaxy S23" --manufacturer "Samsung" --server https://api.ironvault.com
"""
import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime

import requests


def compute_fingerprint(components: dict) -> str:
    parts = "|".join(str(components.get(k, "")) for k in sorted(components.keys()))
    return hashlib.sha256(parts.encode()).hexdigest()


def inject_hardware_ids(args: argparse.Namespace):
    server = args.server.rstrip("/")
    api_key = args.api_key or os.environ.get("IRONVAULT_MANUFACTURER_KEY", "")

    if not api_key:
        print("ERROR: --api-key or IRONVAULT_MANUFACTURER_KEY env var required")
        sys.exit(1)

    components = {
        "imei": args.imei or "",
        "imei2": args.imei2 or "",
        "serial": args.device_serial,
        "model": args.model,
        "manufacturer": args.manufacturer,
        "board": args.board or "",
        "soc_manufacturer": args.soc_manufacturer or "",
        "soc_model": args.soc_model or "",
    }

    fingerprint = compute_fingerprint(components)

    payload = {
        "device_serial": args.device_serial,
        "imei": args.imei,
        "imei2": args.imei2,
        "model": args.model,
        "manufacturer": args.manufacturer,
        "board": args.board,
        "soc_manufacturer": args.soc_manufacturer,
        "soc_model": args.soc_model,
        "hardware_fingerprint": fingerprint,
        "registered_at": datetime.utcnow().isoformat(),
        "batch_id": args.batch_id or str(uuid.uuid4()),
    }

    print(f"\n{'='*60}")
    print(f"IronVault Hardware ID Registration")
    print(f"{'='*60}")
    print(f"Serial:       {args.device_serial}")
    print(f"IMEI:         {args.imei}")
    print(f"Model:        {args.manufacturer} {args.model}")
    print(f"Fingerprint:  {fingerprint}")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("[DRY RUN] Would register the above with the server.")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return

    try:
        resp = requests.post(
            f"{server}/api/manufacturer/register-hardware",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ Successfully registered!")
        print(f"   Registry ID: {data.get('registry_id', 'N/A')}")
        print(f"   Device ID:   {data.get('device_id', 'N/A')}")

        # Save to local CSV log
        with open("registered_devices.csv", "a") as f:
            if os.path.getsize("registered_devices.csv") == 0:
                f.write("timestamp,serial,imei,model,fingerprint,registry_id\n")
            f.write(f"{datetime.utcnow().isoformat()},{args.device_serial},{args.imei or ''},"
                    f"{args.manufacturer} {args.model},{fingerprint},{data.get('registry_id','')}\n")

    except requests.RequestException as e:
        print(f"❌ Failed to register: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="IronVault Hardware ID Injector")
    parser.add_argument("--device-serial", required=True, help="Device serial number")
    parser.add_argument("--imei", help="Primary IMEI")
    parser.add_argument("--imei2", help="Secondary IMEI (dual SIM)")
    parser.add_argument("--model", required=True, help="Device model name")
    parser.add_argument("--manufacturer", required=True, help="Device manufacturer")
    parser.add_argument("--board", help="Board name (Build.BOARD)")
    parser.add_argument("--soc-manufacturer", help="SoC manufacturer")
    parser.add_argument("--soc-model", help="SoC model")
    parser.add_argument("--batch-id", help="Manufacturing batch ID")
    parser.add_argument("--server", default="https://api.ironvault.com",
                        help="IronVault server URL")
    parser.add_argument("--api-key", help="Manufacturer API key")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")

    args = parser.parse_args()
    inject_hardware_ids(args)


if __name__ == "__main__":
    main()
