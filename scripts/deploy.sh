#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/beyond-news}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"
COMPOSE_FILE="${COMPOSE_FILE:-$APP_DIR/docker-compose.prod.yml}"
HEALTHCHECK_URL_DEFAULT="http://127.0.0.1:8000/health"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing env file: $ENV_FILE"
  exit 1
fi

source "$ENV_FILE"

: "${AWS_REGION:?AWS_REGION is required}"
: "${ECR_REGISTRY:?ECR_REGISTRY is required}"
: "${ECR_REPOSITORY:?ECR_REPOSITORY is required}"
: "${IMAGE_TAG:?IMAGE_TAG is required}"

HEALTHCHECK_URL="${HEALTHCHECK_URL:-$HEALTHCHECK_URL_DEFAULT}"
CURRENT_TAG_FILE="$APP_DIR/.current_tag"
PREVIOUS_TAG_FILE="$APP_DIR/.previous_tag"
NEW_TAG="$IMAGE_TAG"

if [[ -f "$CURRENT_TAG_FILE" ]]; then
  cp "$CURRENT_TAG_FILE" "$PREVIOUS_TAG_FILE"
fi

echo "$NEW_TAG" > "$CURRENT_TAG_FILE"

login_ecr() {
  aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"
}

deploy_with_tag() {
  local tag="$1"
  export IMAGE_TAG="$tag"
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" pull
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d
}

health_check() {
  local retries=10
  local delay=3

  for _ in $(seq 1 "$retries"); do
    if curl -fsS "$HEALTHCHECK_URL" >/dev/null; then
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

rollback() {
  if [[ ! -f "$PREVIOUS_TAG_FILE" ]]; then
    echo "rollback skipped: no previous tag"
    return 1
  fi

  local previous_tag
  previous_tag="$(cat "$PREVIOUS_TAG_FILE")"
  echo "rollback to: $previous_tag"
  deploy_with_tag "$previous_tag"
  echo "$previous_tag" > "$CURRENT_TAG_FILE"
  health_check
}

echo "deploying tag: $NEW_TAG"
login_ecr
deploy_with_tag "$NEW_TAG"

if health_check; then
  echo "deployment succeeded"
  exit 0
fi

echo "deployment failed: health check did not pass"
if rollback; then
  echo "rollback succeeded"
  exit 1
fi

echo "rollback failed"
exit 1
