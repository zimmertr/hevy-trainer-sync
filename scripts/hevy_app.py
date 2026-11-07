"""Read what hevy-trainer-sync follows out of a decompiled Hevy Android app, and say whether it changed.

hevy_trainer_sync/trainer_rules.py follows Trainer's rules as the app runs
them, and hevy_trainer_sync/library.py holds the app's built-in exercise
library. Both come from the app, so an app update can change them. This script
fingerprints the app modules holding each followed function and rebuilds the
library, then compares both with what the repo holds. Only fingerprints and the
library's ids, types and equipment are kept, never the app's code. Decision
record 0042.

    python scripts/hevy_app.py check APP.xapk     # exit 3 and a Markdown report if anything changed
    python scripts/hevy_app.py update APP.xapk    # rewrite the fingerprints and library.py

The .xapk is untrusted input: it is only unzipped and decompiled, never run.
"""

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Distinct from Python's own 1, so the workflow can tell a change from a crash.
CHANGED = 3
FINGERPRINTS = ROOT / "scripts" / "hevy_app_fingerprints.json"
LIBRARY = ROOT / "src" / "hevy_trainer_sync" / "library.py"

# Every app function trainer_rules.py follows, by the name the decompiler gives it.
FOLLOWED = (
    "calendarWeekOf", "startOfWeek", "getWeeksInCycle", "getCycleNumber", "getWeekOfCycle", "isDeloadWeek",
    "buildSetContext", "extractExerciseLogs", "extractPreviousExerciseLog", "toExerciseLog",
    "getTrainerExerciseProgression", "getTrainerWeightProgression", "getTrainerRepsProgression",
    "getWeightSuggestionContext", "isSupportedWeightExerciseType", "isSupportedEquipmentCategory",
    "calculateTrainerWeightSuggestion", "decideWeightSuggestion", "decideWeightProgression", "lightenForDeload",
    "evaluateLastPerformance", "computeWeightProgression", "didNotMeetSetCountTarget", "allSetsAtTopOfRange",
    "allSetsBelowBottomOfRange", "nextRepRangeUp", "nextRepRangeDown", "deriveRepsProgression",
    "computeRepsProgression", "calculateTrainerRepsSuggestion", "adjustWeightForEquipment", "adjustForMachine",
    "adjustForDumbbell", "adjustForBarbell", "pickWeight", "pickWeightInDirection", "loadableBarbellWeights",
    "realBarsOrStandardBar", "loadableWeights", "fewestPlatesForEachLoad", "getWeightSuggestionEquipment",
    "calculateWarmupWeights", "toWarmupWeightsSuggestion", "normalizeWarmupSetCount", "weight", "exactLbsToKg",
    "roundToTwoDecimal", "roundToThreeDecimals",
)

# A module this long holds far more than Trainer's rules (the app's shared
# helpers, the whole Trainer store), so only the followed functions in it are
# fingerprinted. A shorter one is fingerprinted whole, which also covers the
# constants it sets up, such as the rep ladder and the warm-up shares.
WHOLE_MODULE_LINES = 1000

_MODULE_START = re.compile(r"^    r\d+ = function\(a0, a1, a2, a3, a4, a5, a6\) \{ // Environment")
_MODULE_END = re.compile(r"^    r\d+ = \d+;$")
# The decompiler numbers every function in the bundle, so one new function
# anywhere renumbers the rest. Those numbers are not part of the logic.
_FUN_ID = re.compile(r"_fun\d+")
_EXERCISE = re.compile(r"\{'id': '([0-9A-F]{8})', 'title': '((?:[^'\\]|\\.)*)'")
_FIELD = "'{}': '([a-z_]+)'"


def modules(lines: list[str], names=FOLLOWED) -> dict[str, list[str]]:
    """Each followed function's module, as its lines, keyed by the module's first followed function."""
    found: dict[int, tuple[int, list[str]]] = {}
    for i, line in enumerate(lines):
        m = re.search(r"// Original name: ([A-Za-z0-9_]+),", line)
        if not m or m.group(1) not in names:
            continue
        start = next((j for j in range(i, -1, -1) if _MODULE_START.match(lines[j])), None)
        if start is None:
            continue
        entry = found.setdefault(start, (i, []))
        if m.group(1) not in entry[1]:
            entry[1].append(m.group(1))
    out = {}
    for start, (_, fns) in sorted(found.items()):
        end = next((j for j in range(start + 1, len(lines)) if _MODULE_END.match(lines[j])), len(lines))
        out[",".join(fns)] = lines[start:end]
    return out


def function_body(lines: list[str], name: str) -> list[str]:
    """The lines of the function the decompiler names `name`, from its first line to its closing brace."""
    start = next((i for i, line in enumerate(lines) if f"// Original name: {name}," in line), None)
    if start is None:
        return []
    depth = 0
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth <= 0 and i > start:
            return lines[start:i + 1]
    return lines[start:]


def fingerprint(body: list[str]) -> str:
    text = _FUN_ID.sub("_fun", "\n".join(body))
    return hashlib.sha256(text.encode()).hexdigest()


def fingerprints(lines: list[str]) -> dict[str, str]:
    out = {}
    for names, body in modules(lines).items():
        if len(body) <= WHOLE_MODULE_LINES:
            out[names] = fingerprint(body)
        else:
            for name in names.split(","):
                # startOfWeek is defined in two modules; keep both.
                key = name if name not in out else f"{name}#2"
                out[key] = fingerprint(function_body(body, name))
    return out


def library(lines: list[str]) -> dict[str, tuple[str, str, str]]:
    """The built-in exercise library: id to title, exercise type and equipment category."""
    out = {}
    for line in lines:
        m = _EXERCISE.search(line)
        if not m:
            continue
        kind = re.search(_FIELD.format("exercise_type"), line)
        equipment = re.search(_FIELD.format("equipment_category"), line)
        if kind and equipment:
            out[m.group(1)] = (m.group(2).replace("\\'", "'"), kind.group(1), equipment.group(1))
    return out


def library_source(lib: dict[str, tuple[str, str, str]], version: str) -> str:
    rows = "\n".join(f"    {k!r}: {v!r}," for k, v in sorted(lib.items()))
    return (
        '"""Hevy\'s built-in exercise library: title, exercise type and equipment for each template id.\n\n'
        "Generated by scripts/hevy_app.py from the Hevy Android app; do not edit by hand. The\n"
        "public API gives no equipment, and Trainer's weight rule rounds to the equipment\n"
        'an exercise uses. Decision record 0042.\n"""\n\n'
        f"APP_VERSION = {version!r}\n\n"
        f"EXERCISES: dict[str, tuple[str, str, str]] = {{\n{rows}\n}}\n"
    )


def compare(old: dict, new: dict) -> list[str]:
    """Plain lines naming every key that was added, removed or changed."""
    lines = []
    for key in sorted(set(old) | set(new)):
        if key not in new:
            lines.append(f"- `{key}` is gone")
        elif key not in old:
            lines.append(f"- `{key}` is new")
        elif old[key] != new[key]:
            lines.append(f"- `{key}` changed")
    return lines


def report(version: str, known: dict, rules: dict[str, str], lib_old: dict, lib_new: dict) -> str | None:
    """A Markdown report of what changed in this app version, or None when nothing did."""
    rule_lines = compare(known.get("modules", {}), rules)
    lib_lines = compare(lib_old, lib_new)
    if not rule_lines and not lib_lines:
        return None
    parts = [f"Hevy app {version} differs from {known.get('app_version', '?')}, the version last checked.", ""]
    if rule_lines:
        parts += ["## Trainer's rules", "", "The modules holding these functions changed. Read them against "
                  "`trainer_rules.py` before trusting the watch's weights again:", "", *rule_lines, ""]
    if lib_lines:
        parts += ["## Exercise library", "", *lib_lines, ""]
    parts += ["Once checked, `python scripts/hevy_app.py update APP.xapk` records this version."]
    return "\n".join(parts)


def decompile(xapk: Path, workdir: Path) -> tuple[str, list[str]]:
    """The app version and the decompiled bundle's lines."""
    with zipfile.ZipFile(xapk) as z:
        manifest = json.loads(z.read("manifest.json"))
        apk = workdir / "base.apk"
        apk.write_bytes(z.read(f"{manifest['package_name']}.apk"))
    with zipfile.ZipFile(apk) as z:
        bundle = workdir / "index.android.bundle"
        bundle.write_bytes(z.read("assets/index.android.bundle"))
    out = workdir / "hevy.js"
    subprocess.run(["hbc-decompiler", str(bundle), str(out)], check=True, capture_output=True)
    return manifest["version_name"], out.read_text(encoding="utf-8", errors="replace").splitlines()


def current_library() -> dict:
    if not LIBRARY.exists():
        return {}
    scope: dict = {}
    exec(compile(LIBRARY.read_text(), str(LIBRARY), "exec"), scope)  # our own generated file
    return dict(scope["EXERCISES"])


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("check", "update"):
        print(__doc__, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        version, lines = decompile(Path(argv[1]), Path(tmp))
    rules, lib = fingerprints(lines), library(lines)
    if argv[0] == "update":
        FINGERPRINTS.write_text(json.dumps({"app_version": version, "modules": rules}, indent=2) + "\n")
        LIBRARY.write_text(library_source(lib, version))
        return 0
    known = json.loads(FINGERPRINTS.read_text())
    text = report(version, known, rules, current_library(), lib)
    if text is None:
        print(f"Hevy app {version}: nothing hevy-trainer-sync follows has changed.")
        return 0
    print(text)
    return CHANGED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
