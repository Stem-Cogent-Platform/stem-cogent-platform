#!/usr/bin/env bash

set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repository_root"

required_files=(
  infrastructure/docker/backend.Dockerfile
  infrastructure/docker/worker.Dockerfile
  infrastructure/docker/frontend.Dockerfile
)

for file in "${required_files[@]}"; do
  test -s "$file" || {
    echo "Required deployment asset is missing or empty: $file" >&2
    exit 1
  }
done

workflow_file=.github/workflows/application-cd.yml
static_identity_matches="$({
  grep -En '^[[:space:]]*role-to-assume:[[:space:]]*arn:aws:iam::' "$workflow_file" || true
  grep -En '^[[:space:]]*(aws-access-key-id|aws-secret-access-key):' "$workflow_file" || true
})"

if [ -n "$static_identity_matches" ]; then
  echo "The application deployment workflow contains a static AWS identity or credential field:" >&2
  echo "$static_identity_matches" >&2
  exit 1
fi

echo "Application CD deployment definition is valid."
