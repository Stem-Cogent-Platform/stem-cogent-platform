#!/usr/bin/env bash

set -euo pipefail

for variable in \
  ECS_CLUSTER_NAME \
  MIGRATION_TASK_DEFINITION \
  ECS_MIGRATION_CONTAINER_NAME \
  ECS_MIGRATION_SUBNET_IDS \
  ECS_MIGRATION_SECURITY_GROUP_IDS; do
  test -n "${!variable:-}" || {
    echo "$variable is required for a one-shot ECS task." >&2
    exit 1
  }
done
test "$#" -gt 0 || {
  echo "A container command is required." >&2
  exit 1
}

jq -n \
  --argjson subnets "$ECS_MIGRATION_SUBNET_IDS" \
  --argjson security_groups "$ECS_MIGRATION_SECURITY_GROUP_IDS" '
    {
      awsvpcConfiguration: {
        subnets: $subnets,
        securityGroups: $security_groups,
        assignPublicIp: "DISABLED"
      }
    }
  ' > one-shot-network.json

command_json="$(printf '%s\n' "$@" | jq -Rsc 'split("\n")[:-1]')"
jq -n \
  --arg container "$ECS_MIGRATION_CONTAINER_NAME" \
  --argjson command "$command_json" \
  '{containerOverrides: [{name: $container, command: $command}]}' \
  > one-shot-overrides.json

aws ecs run-task \
  --cluster "$ECS_CLUSTER_NAME" \
  --task-definition "$MIGRATION_TASK_DEFINITION" \
  --launch-type FARGATE \
  --count 1 \
  --started-by "github-${GITHUB_RUN_ID}" \
  --network-configuration file://one-shot-network.json \
  --overrides file://one-shot-overrides.json > one-shot-run.json

if [ "$(jq '.failures | length' one-shot-run.json)" -ne 0 ]; then
  jq '.failures' one-shot-run.json >&2
  exit 1
fi
task_arn="$(jq -r '.tasks[0].taskArn // empty' one-shot-run.json)"
test -n "$task_arn" || {
  echo "ECS did not return a one-shot task ARN." >&2
  exit 1
}

aws ecs wait tasks-stopped --cluster "$ECS_CLUSTER_NAME" --tasks "$task_arn"
aws ecs describe-tasks \
  --cluster "$ECS_CLUSTER_NAME" \
  --tasks "$task_arn" > one-shot-result.json

exit_code="$(jq -r --arg container "$ECS_MIGRATION_CONTAINER_NAME" \
  '.tasks[0].containers[] | select(.name == $container).exitCode // empty' \
  one-shot-result.json)"
if [ "$exit_code" != "0" ]; then
  jq '{stoppedReason: .tasks[0].stoppedReason, containers: [.tasks[0].containers[] | {name, exitCode, reason, lastStatus}]}' \
    one-shot-result.json >&2
  task_id="${task_arn##*/}"
  log_configuration="$(aws ecs describe-task-definition \
    --task-definition "$MIGRATION_TASK_DEFINITION" \
    --query "taskDefinition.containerDefinitions[?name=='$ECS_MIGRATION_CONTAINER_NAME'].logConfiguration.options | [0]" \
    --output json)"
  log_group="$(jq -r '."awslogs-group" // empty' <<<"$log_configuration")"
  log_prefix="$(jq -r '."awslogs-stream-prefix" // empty' <<<"$log_configuration")"
  if [ -n "$log_group" ] && [ -n "$log_prefix" ]; then
    log_stream="$log_prefix/$ECS_MIGRATION_CONTAINER_NAME/$task_id"
    echo "One-shot container logs ($log_group / $log_stream):" >&2
    for attempt in 1 2 3 4 5; do
      if aws logs get-log-events \
        --log-group-name "$log_group" \
        --log-stream-name "$log_stream" \
        --query 'events[].message' \
        --output text >&2; then
        break
      fi
      sleep 2
    done
  fi
  exit 1
fi
