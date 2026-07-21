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

iam_role_prefix='arn:aws:iam::'
access_key_field='aws-access-key-id'
secret_key_field='aws-secret-access-key'
forbidden_pattern="${iam_role_prefix}(ACCOUNT|[0-9]{12}):|${access_key_field}|${secret_key_field}"

if grep -Eq "$forbidden_pattern" .github/workflows/application-cd.yml; then
  echo "The application deployment workflow contains a static AWS identity or credential field." >&2
  exit 1
fi

echo "Application CD deployment definition is valid."
