#!/bin/sh
set -eu

requested_gib="${1:-}"

if [ -n "$requested_gib" ]; then
  case "$requested_gib" in
    *[!0-9]*|'')
      echo "RAM must be a whole number of GiB" >&2
      exit 2
      ;;
  esac
  detected_gib="$requested_gib"
  source_name="argument"
else
  bytes="$(sysctl -n hw.memsize 2>/dev/null || true)"
  case "$bytes" in
    *[!0-9]*|'')
      echo "Unable to detect Mac memory with sysctl" >&2
      exit 1
      ;;
  esac
  detected_gib=$(( (bytes + 536870912) / 1073741824 ))
  source_name="sysctl"
fi

if [ "$detected_gib" -ge 128 ]; then profile=128
elif [ "$detected_gib" -ge 96 ]; then profile=96
elif [ "$detected_gib" -ge 64 ]; then profile=64
elif [ "$detected_gib" -ge 48 ]; then profile=48
elif [ "$detected_gib" -ge 36 ]; then profile=36
elif [ "$detected_gib" -ge 32 ]; then profile=32
elif [ "$detected_gib" -ge 24 ]; then profile=24
elif [ "$detected_gib" -ge 18 ]; then profile=18
elif [ "$detected_gib" -ge 16 ]; then profile=16
else profile=8
fi

case "$profile" in
  8)   workers=1; light=1; tabs=1; heavy=1; background=0 ;;
  16)  workers=1; light=1; tabs=1; heavy=1; background=1 ;;
  18)  workers=1; light=1; tabs=1; heavy=1; background=1 ;;
  24)  workers=2; light=2; tabs=2; heavy=1; background=1 ;;
  32)  workers=2; light=2; tabs=2; heavy=1; background=1 ;;
  36)  workers=2; light=2; tabs=2; heavy=1; background=1 ;;
  48)  workers=2; light=2; tabs=2; heavy=1; background=1 ;;
  64)  workers=3; light=3; tabs=3; heavy=1; background=2 ;;
  96)  workers=4; light=4; tabs=4; heavy=2; background=3 ;;
  128) workers=5; light=4; tabs=5; heavy=2; background=4 ;;
esac

printf 'source=%s\n' "$source_name"
printf 'detected_gib=%s\n' "$detected_gib"
printf 'profile=%sgb\n' "$profile"
printf 'max_workers=%s\n' "$workers"
printf 'max_light_calls=%s\n' "$light"
printf 'max_browser_tabs=%s\n' "$tabs"
printf 'max_heavy_processes=%s\n' "$heavy"
printf 'max_background_services=%s\n' "$background"
