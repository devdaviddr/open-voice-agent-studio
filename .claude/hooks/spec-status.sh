#!/bin/sh
# SessionStart: show where each spec stands and the open tasks of the MVP.
cd "$(dirname "$0")/../.." || exit 0
echo "Spec status (spec-driven: no code without an approved spec, see spec/README.md):"
for d in spec/*/; do
  f=$(ls -d "$d"*/ 2>/dev/null | sort -V | tail -1)
  [ -n "$f" ] || continue
  status=$(sed -n 's/^status: *//p' "$f/spec.md" | head -1)
  echo "  $(basename "$d") $(basename "$f") [$status]"
done
cur=$(ls -d spec/mvp/*/ 2>/dev/null | sort -V | tail -1)
if [ -n "$cur" ]; then
  open=$(grep -c '\[ \] |$' "$cur/tasks.md" 2>/dev/null || echo 0)
  echo "MVP open tasks: $open (see ${cur}tasks.md)"
fi
