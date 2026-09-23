#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
image=$(docker image inspect dws-application:qualification --format '{{.Id}}')
name="dws-application-$(date +%s)-$$"
volume="$name-state"
docker volume create "$volume"
args=(--rm --network none --cap-drop ALL --security-opt no-new-privileges
  --read-only --memory 1g --memory-swap 1g --cpus 1 --pids-limit 128
  --tmpfs /tmp:rw,noexec,nosuid,size=64m --mount "type=volume,src=$volume,dst=/state"
  --mount "type=bind,src=$PWD/tests/qualification/image_application_probe.py,dst=/probe.py,readonly"
  --mount "type=bind,src=$PWD/docker/image_volume_probe.py,dst=/volume.py,readonly")
printf 'IMAGE=%s VOLUME=%s\n' "$image" "$volume"
for mode in seed persist; do
  docker run --name "$name-$mode" "${args[@]}" "$image" python /probe.py "$mode"
done
for mode in write read; do
  docker run --name "$name-$mode" "${args[@]}" "$image" sh -c 'umask 077; exec python /volume.py "$1"' sh "$mode"
done
# Separate live containers must observe the same advisory lock.
docker run --name "$name-holder" "${args[@]}" "$image" sh -c 'umask 077; exec python /volume.py hold' &
holder=$!
ready=false
for attempt in {1..10}; do
  if docker logs "$name-holder" 2>/dev/null | grep -q LOCK_HELD; then ready=true; break; fi
  sleep 1
done
if [[ $ready != true ]]; then wait "$holder"; exit 1; fi
docker run --name "$name-contend" "${args[@]}" "$image" python /volume.py contend
wait "$holder"
printf 'QUALIFICATION_PASSED image=%s retained_volume=%s\n' "$image" "$volume"
