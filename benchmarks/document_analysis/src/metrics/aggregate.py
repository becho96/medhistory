"""Сводные метрики по run-у и human-readable отчёт."""

from __future__ import annotations

from statistics import mean
from typing import Optional

from benchmarks.document_analysis.src.schema import DatasetDocumentEntry

from .types import DocumentScore, FormatBreakdown, RunAggregate


def aggregate_run(
    per_document: list[DocumentScore],
    manifest_docs: list[DatasetDocumentEntry],
) -> RunAggregate:
    """Усреднить метрики по всем документам прогона + брейк-даун по format."""
    n = len(per_document)
    if n == 0:
        return RunAggregate(
            n_documents=0, n_successful=0, n_failed=0,
            overall_mean=0.0, metadata_mean=0.0,
        )

    # n_failed — где meta.overall == 0 (pipeline вернул дефолт) либо нет вообще
    n_failed = sum(1 for d in per_document if d.metadata.overall == 0.0)
    n_successful = n - n_failed

    overall_mean = round(mean(d.overall for d in per_document), 4)
    metadata_mean = round(mean(d.metadata.overall for d in per_document), 4)

    labs = [d.lab_results for d in per_document if d.lab_results is not None]
    summaries = [d.summary for d in per_document if d.summary is not None]

    lab_f1 = round(mean(l.f1 for l in labs), 4) if labs else None
    lab_val = round(mean(l.value_accuracy for l in labs), 4) if labs else None
    lab_unit = round(mean(l.unit_accuracy for l in labs), 4) if labs else None
    lab_flag = round(mean(l.flag_accuracy for l in labs), 4) if labs else None
    sum_mean = round(mean(s.normalized for s in summaries), 4) if summaries else None

    # Break-down по format. Документы из per_document соединяем с manifest по doc_id.
    fmt_of: dict[str, str] = {d.id: d.format.value for d in manifest_docs}
    by_format_acc: dict[str, list[float]] = {}
    for d in per_document:
        fmt = fmt_of.get(d.doc_id, "unknown")
        by_format_acc.setdefault(fmt, []).append(d.overall)

    by_format = sorted(
        (
            FormatBreakdown(
                format=fmt,
                n_documents=len(scores),
                overall_mean=round(mean(scores), 4),
            )
            for fmt, scores in by_format_acc.items()
        ),
        key=lambda b: b.format,
    )

    return RunAggregate(
        n_documents=n,
        n_successful=n_successful,
        n_failed=n_failed,
        overall_mean=overall_mean,
        metadata_mean=metadata_mean,
        lab_f1_mean=lab_f1,
        lab_value_acc_mean=lab_val,
        lab_unit_acc_mean=lab_unit,
        lab_flag_acc_mean=lab_flag,
        summary_mean=sum_mean,
        by_format=by_format,
    )


def _fmt(v: Optional[float]) -> str:
    return f"{v:.3f}" if v is not None else "n/a"


def render_run_report(
    run_id: str,
    model_id: str,
    judge_model: Optional[str],
    dataset_version: int,
    aggregate: RunAggregate,
    per_document: list[DocumentScore],
) -> str:
    """Сгенерировать markdown-отчёт по одному прогону."""
    lines: list[str] = []
    lines.append(f"# Run `{run_id}`")
    lines.append("")
    lines.append(f"- Model: `{model_id}`")
    lines.append(f"- Dataset: v{dataset_version}")
    lines.append(f"- Judge: `{judge_model}`" if judge_model else "- Judge: disabled")
    lines.append(f"- Documents: {aggregate.n_documents} (successful: {aggregate.n_successful}, failed: {aggregate.n_failed})")
    lines.append("")

    lines.append("## Aggregate")
    lines.append("")
    lines.append("| Metric                       | Value  |")
    lines.append("|------------------------------|--------|")
    lines.append(f"| overall (mean)               | {_fmt(aggregate.overall_mean)} |")
    lines.append(f"| metadata.overall (mean)      | {_fmt(aggregate.metadata_mean)} |")
    lines.append(f"| lab_results.f1 (mean)        | {_fmt(aggregate.lab_f1_mean)} |")
    lines.append(f"| lab_results.value_accuracy   | {_fmt(aggregate.lab_value_acc_mean)} |")
    lines.append(f"| lab_results.unit_accuracy    | {_fmt(aggregate.lab_unit_acc_mean)} |")
    lines.append(f"| lab_results.flag_accuracy    | {_fmt(aggregate.lab_flag_acc_mean)} |")
    lines.append(f"| summary.normalized (mean)    | {_fmt(aggregate.summary_mean)} |")
    lines.append("")

    if aggregate.by_format:
        lines.append("## Break-down by format")
        lines.append("")
        lines.append("| format             | n  | overall |")
        lines.append("|--------------------|----|---------|")
        for b in aggregate.by_format:
            lines.append(f"| {b.format:<18} | {b.n_documents:<2} | {_fmt(b.overall_mean)}   |")
        lines.append("")

    lines.append("## Per-document")
    lines.append("")
    lines.append("| doc_id               | meta  | labs F1 | sum   | overall |")
    lines.append("|----------------------|-------|---------|-------|---------|")
    for d in per_document:
        labs = _fmt(d.lab_results.f1) if d.lab_results else "n/a"
        sm = _fmt(d.summary.normalized) if d.summary else "n/a"
        lines.append(
            f"| {d.doc_id:<20} | {_fmt(d.metadata.overall)} | {labs:<7} | {sm:<5} | {_fmt(d.overall)}   |"
        )

    return "\n".join(lines) + "\n"


def render_compare_report(
    dataset_version: int,
    runs: list[dict],
) -> str:
    """Markdown-таблица сравнения нескольких прогонов на одном датасете.

    `runs` — список словарей вида {run_id, model_id, aggregate: RunAggregate}.
    """
    if not runs:
        return "Нет прогонов для сравнения.\n"

    lines: list[str] = []
    lines.append(f"# Compare runs on dataset v{dataset_version}")
    lines.append("")
    header = ["metric"] + [r["model_id"] for r in runs]
    sep = ["---"] * len(header)
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(sep) + "|")

    rows: list[tuple[str, list[Optional[float]]]] = [
        ("overall (mean)",            [r["aggregate"].overall_mean for r in runs]),
        ("metadata.overall (mean)",   [r["aggregate"].metadata_mean for r in runs]),
        ("lab_results.f1",            [r["aggregate"].lab_f1_mean for r in runs]),
        ("lab_results.value_acc",     [r["aggregate"].lab_value_acc_mean for r in runs]),
        ("lab_results.unit_acc",      [r["aggregate"].lab_unit_acc_mean for r in runs]),
        ("lab_results.flag_acc",      [r["aggregate"].lab_flag_acc_mean for r in runs]),
        ("summary.normalized (mean)", [r["aggregate"].summary_mean for r in runs]),
        ("n_failed",                  [r["aggregate"].n_failed for r in runs]),
    ]
    for label, values in rows:
        lines.append("| " + label + " | " + " | ".join(_fmt(v) if isinstance(v, float) else str(v) for v in values) + " |")
    lines.append("")
    lines.append("Run ids: " + ", ".join(f"`{r['run_id']}`" for r in runs))
    lines.append("")
    return "\n".join(lines)
