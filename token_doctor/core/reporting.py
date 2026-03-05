"""Generate Markdown and JSON reports from normalized event data."""

from __future__ import annotations

import json
from pathlib import Path

from token_doctor.core.schema import (
    CheckStatus,
    PlatformReport,
)


def report_to_markdown(report: PlatformReport) -> str:
    """Render a single platform report as Markdown."""
    lines = [
        f"# {report.platform}",
        "",
        f"*Generated: {report.generated_at.isoformat()}*",
        "",
    ]
    if report.token_checks:
        lines.append("## Token checks")
        lines.append("")
        for c in report.token_checks:
            icon = "✅" if c.status == CheckStatus.OK else "⚠️" if c.status == CheckStatus.WARNING else "❌"
            lines.append(f"- {icon} **{c.name}**: {c.message}")
            if c.endpoint_used:
                lines.append(f"  - Endpoint: `{c.endpoint_used}`")
        lines.append("")
    if report.token_metadata:
        lines.append("## Token metadata")
        lines.append("")
        for k, v in report.token_metadata.items():
            if k.lower() in ("token", "password", "secret"):
                v = "***REDACTED***"
            lines.append(f"- **{k}**: {v}")
        lines.append("")
    lines.append("## Events")
    lines.append("")
    if not report.events:
        lines.append("No change events in cache.")
    else:
        for e in report.events:
            lines.append(f"### {e.title}")
            lines.append("")
            lines.append(f"- **Type**: {e.event_type.value}")
            lines.append(f"- **Confidence**: {e.confidence.value}")
            if e.effective_date:
                lines.append(f"- **Effective date**: {e.effective_date.date()}")
            if e.url:
                lines.append(f"- **URL**: {e.url}")
            lines.append("")
            lines.append(e.description[:500] + ("..." if len(e.description) > 500 else ""))
            lines.append("")
    return "\n".join(lines)


def report_to_json(report: PlatformReport) -> str:
    """Serialize report to JSON (redact any secret fields in token_metadata)."""
    from token_doctor.core.redaction import redact_dict

    data = {
        "platform": report.platform,
        "generated_at": report.generated_at.isoformat(),
        "token_checks": [
            {
                "name": c.name,
                "status": c.status.value,
                "message": c.message,
                "endpoint_used": c.endpoint_used,
                "details": redact_dict(c.details),
            }
            for c in report.token_checks
        ],
        "token_metadata": redact_dict(report.token_metadata),
        "events": [
            {
                "event_type": e.event_type.value,
                "title": e.title,
                "description": e.description,
                "url": e.url,
                "published_at": e.published_at.isoformat() if e.published_at else None,
                "effective_date": e.effective_date.isoformat() if e.effective_date else None,
                "confidence": e.confidence.value,
                "source_type": e.source_type,
                "raw_id": e.raw_id,
            }
            for e in report.events
        ],
    }
    return json.dumps(data, indent=2)


def report_to_html(report: PlatformReport) -> str:
    """Render a single platform report as self-contained HTML."""
    import html

    from token_doctor.core.redaction import redact_dict

    lines = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'><title>token-doctor: " + html.escape(report.platform) + "</title>",
        "<style>body{font-family:system-ui,sans-serif;max-width:800px;margin:1rem auto;padding:0 1rem;}",
        "table{border-collapse:collapse;width:100%;} th,td{border:1px solid #ccc;padding:0.5rem;text-align:left;}",
        ".ok{color:green;} .warning{color:orange;} .error{color:red;}",
        "h1,h2{margin-top:1.5rem;}</style></head><body>",
        "<h1>" + html.escape(report.platform) + "</h1>",
        "<p><em>Generated: " + html.escape(report.generated_at.isoformat()) + "</em></p>",
    ]
    if report.token_checks:
        lines.append("<h2>Token checks</h2><table><tr><th>Check</th><th>Status</th><th>Message</th></tr>")
        for c in report.token_checks:
            cls = "ok" if c.status.value == "ok" else "warning" if c.status.value == "warning" else "error"
            lines.append(
                f"<tr><td>{html.escape(c.name)}</td><td class='{cls}'>{html.escape(c.status.value)}</td>"
                f"<td>{html.escape(c.message)}</td></tr>"
            )
        lines.append("</table>")
    if report.token_metadata:
        lines.append("<h2>Token metadata</h2><ul>")
        for k, v in redact_dict(report.token_metadata).items():
            lines.append(f"<li><strong>{html.escape(str(k))}</strong>: {html.escape(str(v))}</li>")
        lines.append("</ul>")
    lines.append("<h2>Events</h2>")
    if not report.events:
        lines.append("<p>No change events in cache.</p>")
    else:
        lines.append("<table><tr><th>Title</th><th>Type</th><th>Effective date</th><th>URL</th></tr>")
        for e in report.events:
            ed = e.effective_date.date().isoformat() if e.effective_date else ""
            url = f"<a href='{html.escape(e.url)}'>{html.escape(e.url[:50])}...</a>" if e.url else ""
            lines.append(
                f"<tr><td>{html.escape(e.title)}</td><td>{html.escape(e.event_type.value)}</td>"
                f"<td>{ed}</td><td>{url}</td></tr>"
            )
        lines.append("</table>")
    lines.append("</body></html>")
    return "\n".join(lines)


def write_reports(
    report: PlatformReport,
    output_dir: Path,
    base_name: str | None = None,
) -> tuple[Path, Path]:
    """Write Markdown and JSON report files. Returns (md_path, json_path)."""
    base = base_name or report.platform
    md_path = output_dir / f"{base}.md"
    json_path = output_dir / f"{base}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    json_path.write_text(report_to_json(report), encoding="utf-8")
    return md_path, json_path
