import argparse
import os
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a database dump created by pg_dump -Fc.")
    parser.add_argument("dump_file", help="Path to the dump file (.dump)")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    if not os.path.exists(args.dump_file):
        print(f"Dump file not found: {args.dump_file}", file=sys.stderr)
        return 1

    cmd = ["pg_restore", "--clean", "--if-exists", "--no-owner", "-d", database_url, args.dump_file]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("pg_restore failed", file=sys.stderr)
        return result.returncode

    print("Restore completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
