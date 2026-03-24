from __future__ import annotations

import argparse
import json

from src.engine import dish_manager


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview/apply duplicate dish merges.")
    parser.add_argument("--apply", action="store_true", help="Execute merges (default is preview only).")
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive dishes in duplicate detection.",
    )
    args = parser.parse_args()

    result = dish_manager.deduplicate_dishes(
        apply=bool(args.apply),
        include_inactive=bool(args.include_inactive),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
