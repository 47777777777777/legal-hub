"""
backend/updater/cli.py

Command-line interface for the Legal Hub automatic update system.
Default mode is --dry-run; writes occur only when --apply is explicitly specified.
"""

import os
import sys
import yaml
import argparse
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.updater.runner import execute_update_run, log_update_message
from backend.updater.moj import MojSource
from backend.updater.lis import LisSource
from backend.updater.lawplayer import LawplayerSource

CONFIG_PATH = os.path.join(BASE_DIR, "config", "sources.yaml")


def load_sources_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {"sources": []}


def get_source_plugin(name: str, config: dict):
    if name == "moj":
        return MojSource(config)
    elif name == "lis":
        return LisSource(config)
    elif name == "lawplayer":
        return LawplayerSource(config)
    else:
        raise ValueError(f"Unknown source plugin '{name}'")


def main():
    parser = argparse.ArgumentParser(description="Legal Hub Updater CLI (Default: --dry-run)")
    parser.add_argument("--source", choices=["moj", "lis", "lawplayer", "all"], default="all", help="Target data source (default: all)")
    parser.add_argument("--apply", action="store_true", help="Perform live write (default: False/dry-run)")
    parser.add_argument("--confirm-abolish", action="store_true", help="Explicitly approve abolishing > 10 acts (safety valve override)")
    parser.add_argument("--mode", default="manual", help="Execution mode ('manual', 'scheduled', 'canary_test')")
    args = parser.parse_args()

    cfg = load_sources_config()
    sources_list = cfg.get("sources", [])

    targets = [args.source] if args.source != "all" else ["moj", "lis", "lawplayer"]
    print(f"\n=======================================================")
    print(f" Legal Hub Updater CLI")
    print(f" Mode:    {args.mode}")
    print(f" Action:  {'LIVE APPLY' if args.apply else 'DRY RUN (Read Only)'}")
    print(f" Targets: {', '.join(targets)}")
    print(f" Time:    {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=======================================================\n")

    results = {}
    for target in targets:
        src_cfg = next((s for s in sources_list if s.get("name") == target), {})
        if not src_cfg.get("enabled", True):
            print(f"[-] Source '{target}' is disabled in config/sources.yaml. Skipping.")
            continue

        try:
            plugin = get_source_plugin(target, src_cfg)
            res = execute_update_run(plugin, apply=args.apply, mode=args.mode, confirm_abolish=args.confirm_abolish)
            results[target] = res
            print(f"\n>>> Source '{target}' Run Result: status={res.get('status')} <<<")
            if "counts" in res:
                print(f"    Counts: {res['counts']}")
            if "error" in res:
                print(f"    Error:  {res['error']}")
        except Exception as e:
            print(f"[!] Error executing source '{target}': {e}")
            results[target] = {"status": "failed", "error": str(e)}

    print(f"\nAll operations finished.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

