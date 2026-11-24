#!/bin/sh
# Route the placed board with Freerouting (https://github.com/freerouting/freerouting), join the
# ground, and bring it all back into KiCad. Needs Java and the jar:
#   FREEROUTING=/path/to/freerouting.jar tools/route.sh [attempts]
# The router gives a different result every time and does not always finish every connection,
# so the board is routed again until KiCad finds nothing open and nothing wrong.
set -e
JAR="${FREEROUTING:-$HOME/.cache/manent-band-tools/freerouting.jar}"
[ -f "$JAR" ] || { echo "Freerouting jar not found at $JAR: set FREEROUTING"; exit 1; }
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/../electrical/out"
k="$here/kicad.sh"
verdict() { python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
print(len(d['violations']), 'violations,', len(d['unconnected_items']), 'open')" "$out/drc.json"; }
ground_open() { python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
print(sum('[GND]' in str(u) for u in d['unconnected_items']))" "$out/drc.json"; }
signals_open() { python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
print(sum('[GND]' not in str(u) for u in d['unconnected_items']))" "$out/drc.json"; }
# One round: a fresh board, the router's tracks, the ground vias of a file, KiCad's check.
round() { "$k" place > /dev/null; "$k" py gen/pcb_route.py import out/card.ses > /dev/null
          "$k" py gen/pcb_stitch.py apply "$1" > /dev/null 2>&1; "$k" check > /dev/null; }
# Try the vias of out/try.json and drop the ones KiCad objects to, until it objects to none.
settle() { for i in 1 2 3 4 5 6 7 8; do
             round out/try.json
             if "$k" py gen/pcb_stitch.py judge out/try.json out/drc.json out/stitch.json > /dev/null; then return 0; fi
             cp "$out/stitch.json" "$out/try.json"
           done; }
attempt=0
while [ "$attempt" -lt "${1:-6}" ]; do
  attempt=$((attempt + 1))
  if [ -z "$REUSE" ] || [ "$attempt" -gt 1 ]; then   # REUSE=1: start from the out/card.ses already there
    "$k" place > /dev/null
    "$k" py gen/pcb_stitch.py pre out/pre.json > /dev/null     # the router goes around these
    "$k" py gen/pcb_stitch.py apply out/pre.json > /dev/null 2>&1
    "$k" py gen/pcb_route.py export > /dev/null
    (cd "$out" && java -jar "$JAR" -de card.dsn -do card.ses -mp 80 --gui.enabled=false > route.log 2>&1)
    router="$(grep 'Auto-routing stage completed' "$out/route.log" | grep -o '([0-9]* unrouted and [0-9]* violations*)' | tail -1)"
    echo "attempt $attempt: router $router"
  fi
  # The router's own count includes the one ground pin it was left with, so KiCad says whether
  # every signal arrived: nothing but ground may be open before the ground is joined.
  "$k" place > /dev/null; "$k" py gen/pcb_route.py import out/card.ses > /dev/null; "$k" check > /dev/null
  open="$(signals_open)"; echo "  signals open in KiCad: $open"
  [ "$open" = "0" ] || continue
  "$k" py gen/pcb_stitch.py grid out/try.json out/pre.json > /dev/null
  settle
  option=0
  while [ "$option" -lt 24 ]; do            # a via beside each small ground pad, one place at a time
    "$k" py gen/pcb_stitch.py pads out/stitch.json "$option" out/try.json > /dev/null
    settle
    option=$((option + 1))
    [ "$(ground_open)" = "0" ] && break
  done
  cp "$out/stitch.json" "$out/try.json"; settle
  "$k" py gen/pcb_stitch.py islands out/stitch.json out/try.json > /dev/null; settle
  kicad="$(verdict)"; echo "  with the ground joined: KiCad $kicad"
  if [ "$kicad" = "0 violations, 0 open" ]; then
    cp "$out/card.ses" "$out/stitch.json" "$here/../electrical/kicad/"   # kept so `make board` can rebuild them
    exit 0
  fi
done
echo "no clean result in $attempt attempts: the board on disk is the last one"
exit 1
