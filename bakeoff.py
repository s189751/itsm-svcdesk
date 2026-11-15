# ai-generated: 85% - written with an AI assistant from CI-SPEC.md section 3; checked against lab5-practice/expected.json
"""bakeoff.py - scanner SARIF + a labels file -> a per-tool confusion matrix (CI-SPEC.md P-23).

    python3 bakeoff.py --labels labels.json a.sarif b.sarif > bakeoff.json

Standard library only: the grader runs it as `python3 -S -E bakeoff.py`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse

CLASSES = {
    "secret": {259, 260, 321, 798},
    "injection": {74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336},
    "deserialization": {502},
    "weak-crypto": {261, 326, 327, 328, 330, 331, 338, 759, 760, 916},
    "insecure-transport": {295, 297, 319, 322, 757},
    "path-traversal": {22, 23, 35, 36, 73},
    "ssrf": {918},
    "vulnerable-dependency": {937, 1035, 1104, 1395},
    "misconfiguration": {16, 215, 250, 489, 668, 732, 1188},
    "access-control": {284, 285, 639, 862, 863},
}

TOOL_IDS = {
    "trivy": "trivy",
    "grype": "grype",
    "osv-scanner": "osv-scanner",
    "gitleaks": "gitleaks",
    "semgrep": "semgrep",
    "semgrep oss": "semgrep",
    "semgrep ce": "semgrep",
    "semgrep community edition": "semgrep",
    "semgrep pro": "semgrep",
}

CWE_RE = re.compile(r"(?<![A-Za-z0-9])CWE-([0-9]+)", re.IGNORECASE)
TOKEN_RE = re.compile(r"[A-Za-z0-9._-]+")


def _obj(value):
    return value if isinstance(value, dict) else {}


def _arr(value):
    return value if isinstance(value, list) else []


def _get(mapping, key):
    """A member whose value is null counts as absent (P-16)."""
    value = _obj(mapping).get(key)
    return None if value is None else value


def tool_id(run):
    """P-15: the tool id of a run, `unknown` when no usable driver name."""
    name = _get(_get(_get(run, "tool"), "driver"), "name")
    if not isinstance(name, str):
        return "unknown"
    name = name.strip()
    known = TOOL_IDS.get(name.lower())
    if known:
        return known
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "unknown"


def is_run(value):
    return isinstance(value, dict)


def suppressed(result):
    """P-16: true when the result carries a non-empty suppressions member."""
    if "suppressions" not in result:
        return False
    value = result["suppressions"]
    if value is None:
        return False
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return bool(value)


def keep_result(result):
    if not isinstance(result, dict):
        return False
    kind = result.get("kind")
    if kind is not None and kind != "fail":
        return False
    return not suppressed(result)


def first_uri(result):
    """P-16: the uri of the first location's physicalLocation, or None."""
    locations = _arr(result.get("locations"))
    if not locations:
        return None
    physical = _get(_obj(locations[0]), "physicalLocation")
    uri = _get(_get(physical, "artifactLocation"), "uri")
    return uri if isinstance(uri, str) and uri else None


def norm_path(uri):
    """P-17: decode %XX as UTF-8, strip `file://` (any case) and one leading `./`."""
    path = urllib.parse.unquote(uri)
    if path[:7].lower() == "file://":
        path = path[7:]
    if path.startswith("./"):
        path = path[2:]
    return path


def in_set(path, root):
    """P-17: the file from the last component equal to the set root, or None."""
    parts = path.split("/")
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == root:
            return "/".join(parts[index:])
    return None


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def lines_of(result):
    """P-18: (start, end) or (None, None) when the result has no lines."""
    locations = _arr(result.get("locations"))
    if not locations:
        return None, None
    region = _get(_get(locations[0], "physicalLocation"), "region")
    start = _get(region, "startLine")
    if not is_int(start) or start < 1:
        return None, None
    end = _get(region, "endLine")
    if not is_int(end) or end < start:
        end = start
    return start, end


def tags_of(mapping):
    """The string entries of properties.tags of a rule or a result."""
    tags = _get(_get(mapping, "properties"), "tags")
    return [tag for tag in _arr(tags) if isinstance(tag, str)]


def rule_of(run, result):
    """P-19: the first rule of the same run whose id equals the result's ruleId."""
    rule_id = result.get("ruleId")
    if not isinstance(rule_id, str):
        return None
    driver = _get(_get(run, "tool"), "driver")
    for rule in _arr(_get(driver, "rules")):
        if isinstance(rule, dict) and rule.get("id") == rule_id:
            return rule
    return None


def classes_of(result, run, tool):
    """P-19: (a) the result's own class, (b) by tool, (c) CWE tags, (d) other."""
    own = _get(_get(result, "properties"), "class")
    if isinstance(own, str) and own in CLASSES:
        return {own}

    rule = rule_of(run, result)
    if tool == "gitleaks":
        return {"secret"}
    if tool in ("grype", "osv-scanner"):
        return {"vulnerable-dependency"}
    if tool == "trivy" and rule is not None:
        found = set()
        for tag in tags_of(rule):
            lowered = tag.lower()
            if lowered == "vulnerability":
                found.add("vulnerable-dependency")
            elif lowered == "secret":
                found.add("secret")
            elif lowered == "misconfiguration":
                found.add("misconfiguration")
        if found:
            return found

    found = set()
    for tag in tags_of(result) + (tags_of(rule) if rule is not None else []):
        for match in CWE_RE.finditer(tag):
            number = int(match.group(1))
            for name, numbers in CLASSES.items():
                if number in numbers:
                    found.add(name)
    return found or {"other"}


def pep503(name):
    return re.sub(r"[-_.]+", "-", name.lower())


def names_package(text, package):
    """P-20: some token of the message text equals the package name after PEP 503 folding."""
    target = pep503(package)
    for token in TOKEN_RE.findall(text):
        token = token.strip("._-")
        if token and pep503(token) == target:
            return True
    return False


def matches(result, defect, file, classes, lines):
    """P-20: same file, defect class among the result's classes, lines or package."""
    if file != defect.get("file") or defect.get("class") not in classes:
        return False
    if defect.get("class") == "vulnerable-dependency":
        text = _get(_get(result, "message"), "text")
        return isinstance(text, str) and names_package(text, str(defect.get("package", "")))
    start, end = lines
    if start is None:
        return False
    return start <= defect["end_line"] and defect["start_line"] <= end


def confusion_matrix(labels: dict, sarif_documents: list[dict]) -> dict:
    root = labels["set"]
    defects = labels["defects"]
    found: dict[str, set[int]] = {}
    false_positives: dict[str, set] = {}

    for document in sarif_documents:
        for run in _arr(_obj(document).get("runs")):
            if not is_run(run):
                continue
            tool = tool_id(run)
            found.setdefault(tool, set())
            false_positives.setdefault(tool, set())
            for result in _arr(run.get("results")):
                if not keep_result(result):
                    continue
                uri = first_uri(result)
                if uri is None:
                    continue
                file = in_set(norm_path(uri), root)
                if file is None:
                    continue
                lines = lines_of(result)
                classes = classes_of(result, run, tool)
                hit = False
                for index, defect in enumerate(defects):
                    if matches(result, defect, file, classes, lines):
                        found[tool].add(index)
                        hit = True
                if hit:
                    continue
                rule_id = result.get("ruleId")
                rule_id = rule_id if isinstance(rule_id, str) else None
                false_positives[tool].add((rule_id, file, lines[0], lines[1]))

    total = len(defects)
    tools = {}
    for tool in sorted(found):
        tp = len(found[tool])
        fn = total - tp
        fp = len(false_positives[tool])
        precision = round(tp / (tp + fp), 4) if tp + fp else None
        recall = round(tp / total, 4) if total else None
        f1 = round(2 * tp / (2 * tp + fp + fn), 4) if 2 * tp + fp + fn else None
        tools[tool] = {"tp": tp, "fp": fp, "fn": fn,
                       "precision": precision, "recall": recall, "f1": f1}
    return {"set": root, "defects": total, "tools": tools}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="per-tool confusion matrix of SARIF against labels (CI-SPEC.md P-23)")
    parser.add_argument("--labels", required=True, help="the labels file (P-14)")
    parser.add_argument("sarif", nargs="+", help="SARIF 2.1.0 files")
    args = parser.parse_args(argv)
    with open(args.labels, encoding="utf-8") as fh:
        labels = json.load(fh)
    documents = []
    for path in args.sarif:
        with open(path, encoding="utf-8") as fh:
            documents.append(json.load(fh))
    json.dump(confusion_matrix(labels, documents), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
