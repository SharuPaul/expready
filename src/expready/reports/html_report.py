from __future__ import annotations

from pathlib import Path

from expready.models import Report

SEVERITY_LABELS = {
    "error": "Extreme",
    "warning": "Moderate",
    "info": "None",
}


def _display_column_name(column_name: str) -> str:
    overrides = {
        "condition": "Conditions",
        "batch": "Batches",
        "pair": "Pairs",
        "sample_id": "Sample IDs",
    }
    if column_name in overrides:
        return overrides[column_name]
    return column_name.replace("_", " ").title()


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def write_html_report(report: Report, output_path: Path, template_dir: Path | None = None) -> None:
    counts = report.severity_counts
    section_counts = report.section_counts
    action_plan = report.action_plan()
    summary = report.metadata.get("study_summary", {})
    provenance = report.metadata.get("provenance", {})

    summary_blocks: list[str] = []
    if isinstance(summary, dict):
        total = summary.get("total_samples", "NA")
        unique = summary.get("unique_sample_ids", "NA")
        dup = summary.get("duplicate_sample_ids", [])
        dup_text = ", ".join(_escape(value) for value in dup) if dup else "None"
        summary_blocks.append(
            f"""
            <article class="summary-card">
              <div><strong>Total Samples:</strong> {total}</div>
              <div><strong>Unique Sample IDs:</strong> {unique}</div>
              <div><strong>Duplicate Sample IDs:</strong> {dup_text}</div>
            </article>
            """
        )
        columns = summary.get("columns", {})
        if isinstance(columns, dict):
            for column_name, payload in columns.items():
                if not isinstance(payload, dict):
                    continue
                missing = int(payload.get("missing", 0))
                missing_fraction = float(payload.get("missing_fraction", 0.0))
                unique_levels = int(payload.get("unique_levels", 0))
                levels = payload.get("levels", [])
                level_text = []
                for entry in levels:
                    if isinstance(entry, dict):
                        label = _escape(str(entry.get("label", "")))
                        count = _escape(str(entry.get("count", 0)))
                        level_text.append(f"{label}={count}")
                joined = ", ".join(level_text) if level_text else "no non-missing values"
                if missing:
                    joined = f"{joined} (missing={missing})"
                summary_blocks.append(
                    f"""
                    <article class="summary-card">
                      <div><strong>{_escape(_display_column_name(str(column_name)))}</strong></div>
                      <div>{joined}</div>
                      <div class="muted">Unique levels: {unique_levels} | Missing values: {missing} ({missing_fraction:.1%})</div>
                    </article>
                    """
                )
        condition_stats = summary.get("condition_stats", {})
        if isinstance(condition_stats, dict) and condition_stats:
            ratio = condition_stats.get("imbalance_ratio")
            ratio_text = f"{ratio:.2f}" if isinstance(ratio, (int, float)) else "NA"
            summary_blocks.append(
                f"""
                <article class="summary-card">
                  <div><strong>Condition balance</strong></div>
                  <div>Groups: {condition_stats.get('group_count', 'NA')}</div>
                  <div>Minimum/Maximum group size: {condition_stats.get('min_group_size', 'NA')} / {condition_stats.get('max_group_size', 'NA')}</div>
                  <div class="muted">Imbalance ratio: {ratio_text}</div>
                </article>
                """
            )

    issue_sections = {"metadata": [], "design": [], "cross_file": [], "general": []}
    for issue in report.sorted_issues():
        issue_sections.setdefault(issue.section, []).append(issue)

    section_badges = []
    for section_name in ["metadata", "design", "cross_file", "general"]:
        section_payload = section_counts.get(section_name)
        if not section_payload:
            continue
        section_title = section_name.replace("_", " ").title()
        section_badges.append(
            f"""<span class="pill">{_escape(section_title)}: {section_payload['total']} """
            f"""({SEVERITY_LABELS['error'][0]}:{section_payload['error']} """
            f"""{SEVERITY_LABELS['warning'][0]}:{section_payload['warning']} """
            f"""{SEVERITY_LABELS['info'][0]}:{section_payload['info']})</span>"""
        )

    issue_blocks = []
    for section_name in ["metadata", "design", "cross_file", "general"]:
        section_issues = issue_sections.get(section_name, [])
        if not section_issues:
            continue
        section_title = section_name.replace("_", " ").title()
        section_block = [f'<section class="issue-section"><h3>{_escape(section_title)}</h3><div class="issue-list">']
        for issue in section_issues:
            section_block.append(
                f"""
                <article class="issue issue-card issue-{_escape(issue.severity.value)} section-{_escape(issue.section)}" data-severity="{_escape(issue.severity.value)}" data-section="{_escape(issue.section)}">
                  <div class="rule">{_escape(issue.title)}</div>
                  <div class="severity-{_escape(issue.severity.value)}">Severity: {_escape(SEVERITY_LABELS.get(issue.severity.value, issue.severity.value.title()))}</div>
                  <p>{_escape(issue.description)}</p>
                  <p><strong>Why it matters:</strong> {_escape(issue.rationale)}</p>
                  <p><strong>What to do:</strong> {_escape(issue.suggested_fix)}</p>
                </article>
                """
            )
        section_block.append("</div></section>")
        issue_blocks.append("".join(section_block))

    plan_blocks = []
    for item in action_plan[:8]:
        plan_blocks.append(
            f"""
            <article class="summary-card">
              <div><strong>{_escape(item['step'])}</strong> ({_escape(item['priority']).title()} priority)</div>
              <div>{_escape(item['title'])}</div>
              <div class="muted">{_escape(item['suggested_fix'])}</div>
            </article>
            """
        )

    provenance_block = ""
    if isinstance(provenance, dict) and provenance:
        provenance_block = f"""
        <section class="report-section">
          <h2>Run Details</h2>
          <article class="summary-card">
            <div><strong>Tool:</strong> {_escape(str(provenance.get('tool_name', 'NA')))} {_escape(str(provenance.get('tool_version', '')))}</div>
            <div><strong>Generated:</strong> {_escape(str(provenance.get('generated_at_utc', 'NA')))}</div>
            <div><strong>Command:</strong> <code>{_escape(str(provenance.get('command', 'NA')))}</code></div>
          </article>
        </section>
        """

    banner_color = "#b91c1c" if report.status == "fail" else "#0f766e"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Experiment-Readiness Checker Readiness Report</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --panel: #ffffff;
      --ink: #0f172a;
      --error: #b42318;
      --warning: #b54708;
      --info: #175cd3;
      --border: #d0d5dd;
      --muted: #475467;
      --section: #eaecf0;
    }}
    body {{ font-family: "Source Sans 3", "Calibri", "Arial", sans-serif; background: radial-gradient(circle at top right, #eef4ff 0%, var(--bg) 40%); color: var(--ink); margin: 0; padding: 2rem; line-height: 1.45; }}
    .card {{ max-width: 1040px; margin: 0 auto; background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 1.3rem 1.6rem; box-shadow: 0 10px 32px rgba(16, 24, 40, 0.07); }}
    .banner {{ padding: 0.9rem 1rem; border-radius: 10px; margin-bottom: 1rem; font-weight: 700; color: white; background: {banner_color}; letter-spacing: 0.2px; }}
    .report-section {{ border-top: 1px solid var(--border); margin-top: 1.1rem; padding-top: 1rem; }}
    .report-section h2 {{ margin-top: 0; margin-bottom: 0.7rem; font-size: 1.24rem; letter-spacing: 0.15px; }}
    .counts {{ display: flex; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }}
    .pill {{ border: 1px solid var(--border); border-radius: 999px; padding: 0.32rem 0.8rem; font-size: 0.97rem; background: #f8fafc; }}
    .filters {{ display: flex; gap: 0.5rem; margin: 0.5rem 0 1rem 0; flex-wrap: wrap; }}
    .btn {{ border: 1px solid var(--border); background: white; border-radius: 8px; padding: 0.32rem 0.7rem; cursor: pointer; color: var(--ink); }}
    .btn.active {{ border-color: #344054; background: #eef2f6; font-weight: 600; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 0.7rem; margin-bottom: 1rem; }}
    .summary-card {{ border: 1px solid var(--border); border-radius: 10px; padding: 0.65rem 0.82rem; background: #fcfcfd; }}
    .muted {{ color: var(--muted); font-size: 0.95rem; margin-top: 0.3rem; }}
    .issue-section {{ border: 1px solid var(--section); border-radius: 12px; padding: 0.8rem 0.9rem; margin-bottom: 1rem; background: #fbfcfe; }}
    .issue-section h3 {{ margin: 0 0 0.35rem 0; font-size: 1.08rem; padding-bottom: 0.45rem; border-bottom: 1px solid var(--section); }}
    .issue-list {{ display: block; }}
    .issue {{ border-top: 1px solid var(--section); padding: 0.75rem 0; }}
    .issue:first-of-type {{ border-top: 0; }}
    .rule {{ font-weight: 700; font-size: 1.06rem; }}
    .severity-error {{ color: var(--error); }}
    .severity-warning {{ color: var(--warning); }}
    .severity-info {{ color: var(--info); }}
    code {{ background: #f2f4f7; padding: 0.1rem 0.3rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <main class="card">
    <div class="banner">Overall Status: {report.status.upper()}</div>
    <section class="report-section">
      <h2>Summary</h2>
      <div class="summary-grid">
        {''.join(summary_blocks) if summary_blocks else '<article class="summary-card">No summary data available.</article>'}
      </div>
    </section>
    <section class="report-section">
      <h2>Issue Levels</h2>
      <div class="counts">
      <span class="pill">{SEVERITY_LABELS['error']}: {counts['error']}</span>
      <span class="pill">{SEVERITY_LABELS['warning']}: {counts['warning']}</span>
      <span class="pill">{SEVERITY_LABELS['info']}: {counts['info']}</span>
      {''.join(section_badges)}
      </div>
    </section>
    <section class="report-section">
      <h2>Action Plan</h2>
      <div class="summary-grid">
        {''.join(plan_blocks) if plan_blocks else '<article class="summary-card">No actions needed.</article>'}
      </div>
    </section>
    <section class="report-section">
      <h2>Issues</h2>
      <p class="muted">These are grouped by section. Use the filters to focus on what matters right now.</p>
      <div class="filters">
        <button class="btn active" onclick="setSeverityFilter('all', this)">All Levels</button>
        <button class="btn" onclick="setSeverityFilter('error', this)">{SEVERITY_LABELS['error']}</button>
        <button class="btn" onclick="setSeverityFilter('warning', this)">{SEVERITY_LABELS['warning']}</button>
        <button class="btn" onclick="setSeverityFilter('info', this)">{SEVERITY_LABELS['info']}</button>
      </div>
      <div class="filters">
        <button class="btn active" onclick="setSectionFilter('all', this)">All Sections</button>
        <button class="btn" onclick="setSectionFilter('metadata', this)">Metadata</button>
        <button class="btn" onclick="setSectionFilter('design', this)">Design</button>
        <button class="btn" onclick="setSectionFilter('cross_file', this)">Cross-File</button>
      </div>
      {''.join(issue_blocks)}
    </section>
    {provenance_block}
    <section class="report-section">
      <h2>How to Use This Report</h2>
      <p>Fix <strong>{SEVERITY_LABELS['error']}</strong> issues first. Then review <strong>{SEVERITY_LABELS['warning']}</strong> issues. <strong>{SEVERITY_LABELS['info']}</strong> means no concern for that check.</p>
    </section>
  </main>
  <script>
    let severityFilter = 'all';
    let sectionFilter = 'all';
    function updateFilters() {{
      document.querySelectorAll('.issue-card').forEach((card) => {{
        const okSeverity = severityFilter === 'all' || card.dataset.severity === severityFilter;
        const okSection = sectionFilter === 'all' || card.dataset.section === sectionFilter;
        card.style.display = (okSeverity && okSection) ? '' : 'none';
      }});
    }}
    function markActive(button) {{
      const parent = button.parentElement;
      parent.querySelectorAll('.btn').forEach((b) => b.classList.remove('active'));
      button.classList.add('active');
    }}
    function setSeverityFilter(value, button) {{
      severityFilter = value;
      markActive(button);
      updateFilters();
    }}
    function setSectionFilter(value, button) {{
      sectionFilter = value;
      markActive(button);
      updateFilters();
    }}
  </script>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
