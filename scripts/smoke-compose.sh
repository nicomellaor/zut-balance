#!/usr/bin/env bash
set -euo pipefail

project="zut-balance-smoke"
environment_file="tests/compose.env"
https_port="${ZUT_BALANCE_SMOKE_HTTPS_PORT:-18443}"
export ZUT_BALANCE_HTTPS_PORT="$https_port"
compose=(docker compose --project-name "$project" --env-file "$environment_file")
cleanup() { "${compose[@]}" down --volumes --remove-orphans; }
trap cleanup EXIT

"${compose[@]}" --profile manual config --format json | python -c '
import json
import sys

services = json.load(sys.stdin)["services"]
if services["caddy"].get("restart") != "always":
    raise SystemExit("caddy must use restart: always")
if services["api"].get("restart") != "always":
    raise SystemExit("api must use restart: always")
if "restart" in services["backup"] or services["backup"].get("profiles") != ["manual"]:
    raise SystemExit("backup must remain a manual one-shot service")
'

"${compose[@]}" up --build --detach
for _ in {1..30}; do
    if "${compose[@]}" exec -T caddy test -f /data/caddy/pki/authorities/local/root.crt; then
        break
    fi
    sleep 1
done
"${compose[@]}" cp caddy:/data/caddy/pki/authorities/local/root.crt /tmp/zut-balance-smoke-ca.crt
curl=(curl --silent --show-error --fail --cacert /tmp/zut-balance-smoke-ca.crt --resolve "zut-balance.test:${https_port}:127.0.0.1")
for _ in {1..30}; do
    if "${curl[@]}" "https://zut-balance.test:${https_port}/health" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
"${curl[@]}" "https://zut-balance.test:${https_port}/health" >/dev/null
"${compose[@]}" restart api
for _ in {1..30}; do
    if "${curl[@]}" "https://zut-balance.test:${https_port}/health" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
"${curl[@]}" "https://zut-balance.test:${https_port}/health" >/dev/null
"${curl[@]}" "https://zut-balance.test:${https_port}/" >/dev/null
"${curl[@]}" --cookie-jar /tmp/zut-balance-smoke.cookies --header 'Content-Type: application/json' --data '{"password":"admin-password"}' "https://zut-balance.test:${https_port}/v1/auth/login" >/dev/null
"${curl[@]}" --cookie /tmp/zut-balance-smoke.cookies "https://zut-balance.test:${https_port}/v1/statements" >/dev/null
"${curl[@]}" --header 'Authorization: Bearer synthetic-integration-key-only-for-compose-smoke' "https://zut-balance.test:${https_port}/v1/statements" >/dev/null
"${compose[@]}" run --rm backup >/dev/null
if "${compose[@]}" port api 8000 >/dev/null 2>&1; then
    exit 1
fi
