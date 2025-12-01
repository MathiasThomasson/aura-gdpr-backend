import argparse
import datetime
import os
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump the database to a timestamped file.")
    parser.add_argument("-o", "--output", help="Output file path", default=None)
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    output = args.output or f"backup_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.dump"

    cmd = ["pg_dump", database_url, "-Fc", "-f", output]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("pg_dump failed", file=sys.stderr)
        return result.returncode

    print(f"Backup written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
