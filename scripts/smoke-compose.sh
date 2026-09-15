#!/usr/bin/env bash
set -euo pipefail

project="zut-balance-smoke"
environment_file="tests/compose.env"
compose=(docker compose --project-name "$project" --env-file "$environment_file")
cleanup() { "${compose[@]}" down --volumes --remove-orphans; }
trap cleanup EXIT

"${compose[@]}" up --build --detach
for _ in {1..30}; do
    if "${compose[@]}" exec -T caddy test -f /data/caddy/pki/authorities/local/root.crt; then
        break
    fi
    sleep 1
done
"${compose[@]}" cp caddy:/data/caddy/pki/authorities/local/root.crt /tmp/zut-balance-smoke-ca.crt
curl=(curl --silent --show-error --fail --cacert /tmp/zut-balance-smoke-ca.crt --resolve zut-balance.test:8443:127.0.0.1)
for _ in {1..30}; do
    if "${curl[@]}" https://zut-balance.test:8443/health >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
"${curl[@]}" https://zut-balance.test:8443/health >/dev/null
"${curl[@]}" https://zut-balance.test:8443/ >/dev/null
"${curl[@]}" --cookie-jar /tmp/zut-balance-smoke.cookies --header 'Content-Type: application/json' --data '{"password":"admin-password"}' https://zut-balance.test:8443/v1/auth/login >/dev/null
"${curl[@]}" --cookie /tmp/zut-balance-smoke.cookies https://zut-balance.test:8443/v1/statements >/dev/null
"${curl[@]}" --header 'Authorization: Bearer synthetic-integration-key-only-for-compose-smoke' https://zut-balance.test:8443/v1/statements >/dev/null
"${compose[@]}" run --rm backup >/dev/null
if "${compose[@]}" port api 8000 >/dev/null 2>&1; then
    exit 1
fi
