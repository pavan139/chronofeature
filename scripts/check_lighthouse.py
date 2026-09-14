"""Report all Lighthouse runs and gate their median, retaining raw artifacts."""
import json
from pathlib import Path
from statistics import median

reports = [json.loads(path.read_text()) for path in sorted(Path("test-results").glob("lighthouse-*.json"))]
assert len(reports) == 3, "Expected three complete Lighthouse reports"
runs = [
    {name: round(value["score"] * 100) for name, value in report["categories"].items()}
    for report in reports
]
scores = {name: median(run[name] for run in runs) for name in runs[0]}
print("ASTRO_LIGHTHOUSE_RUNS=" + json.dumps(runs))
print("ASTRO_LIGHTHOUSE=" + json.dumps(scores))
metrics = {}
for key in ["largest-contentful-paint", "cumulative-layout-shift", "total-blocking-time"]:
    values = [report["audits"][key]["numericValue"] for report in reports]
    metrics[key] = {"runs": values, "median": median(values)}
print("ASTRO_METRICS=" + json.dumps(metrics))
failures = {}
for report in reports:
    for key, audit in report["audits"].items():
        if audit.get("score") == 0:
            failures[key] = {field: audit.get(field) for field in ["title", "displayValue", "details"]}
print("ASTRO_AUDIT_FAILURES=" + json.dumps(failures))
print("ASTRO_ENVIRONMENT=" + json.dumps([r.get("environment") for r in reports]))
assert scores["performance"] >= 90 and scores["accessibility"] >= 90 and scores["seo"] >= 90, scores
