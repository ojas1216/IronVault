#!/usr/bin/env python3
"""
IronVault Manufacturer Tool — Emergency Remote Wipe
Sends factory reset command to all stolen/specified devices.

⚠️  DESTRUCTIVE OPERATION — Cannot be undone.

Usage:
  # Preview what would be wiped (safe)
  python remote_wipe_all.py --status stolen --dry-run

  # Wipe all stolen devices (requires --confirm)
  python remote_wipe_all.py --status stolen --confirm

  # Wipe a specific device
  python remote_wipe_all.py --device-id <UUID> --confirm

  # Wipe devices that have been offline > N days and are marked stolen
  python remote_wipe_all.py --status stolen --offline-days 30 --confirm
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests


def get_devices(server: str, api_key: str, status: str = None, device_id: str = None) -> list:
    headers = {"Authorization": f"Bearer {api_key}"}
    if device_id:
        resp = requests.get(f"{server}/api/admin/devices/{device_id}", headers=headers, timeout=15)
        resp.raise_for_status()
        return [resp.json()["device"]]
    else:
        params = {}
        if status:
            params["status"] = status
        resp = requests.get(f"{server}/api/admin/devices", headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()["devices"]


def send_wipe(server: str, api_key: str, device_id: str) -> dict:
    resp = requests.post(
        f"{server}/api/admin/wipe",
        params={"device_id": device_id},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    if resp.status_code == 200:
        return {"success": True, "data": resp.json()}
    else:
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}


def filter_by_offline_days(devices: list, offline_days: int) -> list:
    from datetime import timezone
    now = datetime.now(timezone.utc)
    result = []
    for d in devices:
        if not d.get("last_seen"):
            result.append(d)
            continue
        last_seen = datetime.fromisoformat(d["last_seen"].replace("Z", "+00:00"))
        diff_days = (now - last_seen).days
        if diff_days >= offline_days:
            result.append(d)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="IronVault Emergency Remote Wipe Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--device-id", help="Wipe a single device")
    group.add_argument("--status", choices=["stolen", "active", "wiping"],
                       help="Wipe all devices with this status")

    parser.add_argument("--offline-days", type=int,
                        help="Only wipe devices offline for this many days")
    parser.add_argument("--confirm", action="store_true",
                        help="Required to actually perform wipe (not dry-run)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview which devices would be wiped")
    parser.add_argument("--server", default=os.environ.get("IRONVAULT_SERVER", "https://api.ironvault.com"))
    parser.add_argument("--api-key",
                        default=os.environ.get("IRONVAULT_API_KEY", ""),
                        help="Admin API key")
    parser.add_argument("--output", help="Save results to JSON file")
    parser.add_argument("--rate-limit", type=float, default=0.5,
                        help="Seconds between each wipe command (default: 0.5)")

    args = parser.parse_args()

    if not args.confirm and not args.dry_run:
        print("ERROR: Must specify --confirm or --dry-run")
        sys.exit(1)

    api_key = args.api_key
    if not api_key:
        print("ERROR: --api-key or IRONVAULT_API_KEY env var required")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"IronVault Emergency Remote Wipe")
    print(f"Server: {args.server}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    # Get target devices
    print("Fetching device list...")
    devices = get_devices(args.server, api_key, args.status, args.device_id)
    print(f"Found {len(devices)} device(s) matching criteria")

    # Apply offline filter
    if args.offline_days:
        devices = filter_by_offline_days(devices, args.offline_days)
        print(f"After offline filter (≥{args.offline_days} days): {len(devices)} device(s)")

    if not devices:
        print("No devices to wipe.")
        return

    # Preview
    print(f"\nDevices to be wiped:")
    print(f"{'Device Name':<30} {'Owner':<20} {'Status':<12} {'Last Seen'}")
    print("-" * 80)
    for d in devices:
        print(f"{d.get('device_name','N/A'):<30} {d.get('owner_name','N/A'):<20} "
              f"{d.get('status','?'):<12} {d.get('last_seen','Never')}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would send wipe command to {len(devices)} device(s).")
        return

    # Final confirmation
    if len(devices) > 1:
        confirm_text = input(f"\n⚠️  About to wipe {len(devices)} devices. Type 'WIPE ALL' to confirm: ")
        if confirm_text != "WIPE ALL":
            print("Aborted.")
            sys.exit(0)

    # Execute wipes
    results = []
    success = 0
    failed = 0

    print(f"\nSending wipe commands...")
    for i, device in enumerate(devices, 1):
        device_id = device["id"]
        device_name = device.get("device_name", device_id)
        print(f"[{i}/{len(devices)}] Wiping {device_name}...", end=" ")

        result = send_wipe(args.server, api_key, device_id)
        if result["success"]:
            print("✅ Command sent")
            success += 1
        else:
            print(f"❌ Failed: {result['error']}")
            failed += 1

        results.append({
            "device_id": device_id,
            "device_name": device_name,
            "success": result["success"],
            "error": result.get("error"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        time.sleep(args.rate_limit)

    print(f"\n{'='*60}")
    print(f"Wipe Results: {success} succeeded, {failed} failed")
    print(f"{'='*60}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump({"results": results, "summary": {"success": success, "failed": failed,
                       "total": len(devices), "executed_at": datetime.now(timezone.utc).isoformat()}
                       }, f, indent=2)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
