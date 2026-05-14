"""CLI бенчмарка первичного анализа документов.

Запуск:
    python -m benchmarks.document_analysis.src.cli run \\
        --dataset v1 --model gemini-2.5-flash

    python -m benchmarks.document_analysis.src.cli run \\
        --dataset v1 --model gemini-2.5-flash --doc doc_001

    python -m benchmarks.document_analysis.src.cli validate-dataset --dataset v1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BENCHMARK_ROOT.parents[1]


def _load_env_file() -> None:
    """Подгрузить переменные из .env.local (репозиторий) до импорта backend.

    AIService через `app.core.config.Settings()` требует обязательные переменные
    (OPENROUTER_API_KEY, DATABASE_URL, JWT_SECRET и др.) — Settings сам .env-файл
    не читает, поэтому делаем это здесь. Существующие переменные окружения
    имеют приоритет (load_dotenv не перетирает).
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None  # рассчитываем на окружение, которое выставил пользователь

    if load_dotenv is not None:
        env_file = os.environ.get("MEDHISTORY_ENV_FILE") or str(REPO_ROOT / ".env.local")
        if Path(env_file).exists():
            load_dotenv(env_file)

    # Поля, которые Settings() требует, но pipeline извлечения документов не использует
    # (БД и MinIO нужны document_service, а не AIService). Подставляем заглушки,
    # чтобы Settings() инициализировался на хосте без docker-compose окружения.
    for var in ("DATABASE_URL", "MONGODB_URL", "MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"):
        os.environ.setdefault(var, "benchmark-stub")


_load_env_file()


def _detect_backend_root() -> Path:
    """Найти корень backend, чтобы импортировать prod-AIService.

    Порядок: MEDHISTORY_BACKEND_PATH → repo/backend → /app (раскладка контейнера).
    """
    env = os.environ.get("MEDHISTORY_BACKEND_PATH")
    if env:
        return Path(env)
    for candidate in (REPO_ROOT / "backend", Path("/app")):
        if (candidate / "app" / "__init__.py").exists():
            return candidate
    raise RuntimeError(
        "Не нашёл backend (app/__init__.py). Задайте MEDHISTORY_BACKEND_PATH "
        "или запускайте из репозитория."
    )


BACKEND_ROOT = _detect_backend_root()
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from benchmarks.document_analysis.src.runner import (  # noqa: E402
    BenchmarkAIService,
    compute_prompt_versions,
    run_one_document,
    sha256_of_file,
)
from benchmarks.document_analysis.src.metrics import (  # noqa: E402
    DocumentScore,
    aggregate_run,
    env_api_key,
    env_base_url,
    render_compare_report,
    render_run_report,
    score_lab_results,
    score_metadata,
    score_summary,
)
from benchmarks.document_analysis.src.schema import (  # noqa: E402
    DatasetDocumentEntry,
    GroundTruth,
    Prediction,
    RunMeta,
    dump_json,
    load_ground_truth,
    load_manifest,
    load_models_registry,
)
from benchmarks.document_analysis.src.synonyms import (  # noqa: E402
    fetch_index_from_db,
    load_index,
    save_cache,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def cmd_run(args: argparse.Namespace) -> None:
    registry = load_models_registry(BENCHMARK_ROOT / "models.yaml")
    try:
        model_cfg = registry.find_extraction_model(args.model)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    dataset_dir = BENCHMARK_ROOT / "datasets" / args.dataset
    manifest = load_manifest(dataset_dir / "manifest.yaml")

    documents = manifest.documents
    if args.doc:
        documents = [d for d in documents if d.id == args.doc]
        if not documents:
            print(f"❌ Документ '{args.doc}' не найден в manifest.")
            sys.exit(1)

    if not documents:
        print(
            "⚠️  manifest.yaml.documents пуст. Добавьте описания документов "
            "и положите файлы в datasets/<v>/documents/."
        )
        sys.exit(1)

    run_slug = f"{_now_slug()}_{model_cfg.id}_v{manifest.version}"
    run_dir = BENCHMARK_ROOT / "runs" / run_slug
    (run_dir / "predictions").mkdir(parents=True, exist_ok=True)

    ai = BenchmarkAIService(
        model_id=model_cfg.id,
        openrouter_slug=model_cfg.openrouter_slug,
        temperature=model_cfg.temperature,
    )

    run_meta = RunMeta(
        run_id=run_slug,
        started_at=_now_iso(),
        dataset_version=manifest.version,
        model=model_cfg,
        prompt_versions=compute_prompt_versions(ai),
        git_commit=_git_commit(),
        total_documents=len(documents),
    )

    print(f"🚀 Run: {run_slug}")
    print(f"   Model:    {model_cfg.openrouter_slug}  (temp={model_cfg.temperature})")
    print(f"   Dataset:  v{manifest.version} ({len(documents)} док.)")
    print(f"   Prompts:  {run_meta.prompt_versions}")
    print()

    asyncio.run(_run_all(ai, dataset_dir, documents, run_dir, run_meta))


async def _run_all(
    ai: BenchmarkAIService,
    dataset_dir: Path,
    documents: list[DatasetDocumentEntry],
    run_dir: Path,
    run_meta: RunMeta,
) -> None:
    successful = 0
    failed = 0

    for doc in documents:
        doc_path = dataset_dir / "documents" / doc.file
        if not doc_path.exists():
            print(f"⚠️  {doc.id}: файл не найден — {doc.file}")
            failed += 1
            continue

        actual_sha = sha256_of_file(doc_path)
        if actual_sha != doc.sha256:
            print(f"⚠️  {doc.id}: sha256 не совпадает с manifest. expected={doc.sha256[:10]}.., got={actual_sha[:10]}..")
            # Пропускаем, чтобы не закрепить ошибочный baseline на изменённом файле.
            failed += 1
            continue

        print(f"▶  {doc.id} ({doc.format})")
        pred = await run_one_document(ai, doc_path, doc.id)
        dump_json(pred, run_dir / "predictions" / f"{doc.id}.json")

        if pred.error:
            print(f"   ⚠️ error: {pred.error[:120]}")
            failed += 1
        else:
            n_labs = len(pred.lab_results)
            print(f"   ✅ type={pred.metadata.document_type!r} labs={n_labs}")
            successful += 1

    run_meta.completed_at = _now_iso()
    run_meta.successful = successful
    run_meta.failed = failed
    dump_json(run_meta, run_dir / "run_meta.json")

    print()
    print(f"✅ Готово. successful={successful} failed={failed}")
    print(f"   Артефакты: {run_dir.relative_to(REPO_ROOT)}")


def cmd_score(args: argparse.Namespace) -> None:
    """Посчитать метрики (metadata + lab_results + summary) для существующего прогона."""
    run_dir = BENCHMARK_ROOT / "runs" / args.run
    if not run_dir.exists():
        print(f"❌ Run-папка не найдена: {run_dir}")
        sys.exit(1)

    meta_path = run_dir / "run_meta.json"
    if not meta_path.exists():
        print(f"❌ Нет run_meta.json в {run_dir}")
        sys.exit(1)
    meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
    dataset_version = meta_data["dataset_version"]
    dataset_dir = BENCHMARK_ROOT / "datasets" / f"v{dataset_version}"

    cache_path = BENCHMARK_ROOT / ".cache" / "synonyms.json"
    try:
        synonyms_idx = load_index(cache_path)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    pred_files = sorted((run_dir / "predictions").glob("*.json"))
    if not pred_files:
        print(f"❌ В {run_dir / 'predictions'} нет файлов predictions.")
        sys.exit(1)

    registry = load_models_registry(BENCHMARK_ROOT / "models.yaml")
    judge = registry.judge

    print(f"📊 Scoring {len(pred_files)} predictions против v{dataset_version}")
    print(f"   Synonyms index: {synonyms_idx.size()}")
    if args.no_summary:
        print("   Summary judge: DISABLED (--no-summary)")
    else:
        print(f"   Summary judge: {judge.openrouter_slug}")
    print()

    asyncio.run(_score_all(
        pred_files=pred_files,
        dataset_dir=dataset_dir,
        synonyms_idx=synonyms_idx,
        judge=judge,
        run_dir=run_dir,
        run_id=args.run,
        dataset_version=dataset_version,
        model_id=meta_data["model"]["id"],
        skip_summary=args.no_summary,
    ))


async def _score_all(
    pred_files,
    dataset_dir,
    synonyms_idx,
    judge,
    run_dir,
    run_id: str,
    dataset_version: int,
    model_id: str,
    skip_summary: bool,
) -> None:
    judge_cache_dir = BENCHMARK_ROOT / ".cache" / "judge"
    api_key = None
    base_url = None
    if not skip_summary:
        try:
            api_key = env_api_key()
        except RuntimeError as e:
            print(f"❌ {e}")
            sys.exit(1)
        base_url = env_base_url()

    per_document: list[DocumentScore] = []
    skipped = 0
    for pf in pred_files:
        doc_id = pf.stem
        pred = Prediction.model_validate_json(pf.read_text(encoding="utf-8"))
        gt_path = dataset_dir / "ground_truth" / f"{doc_id}.json"
        if not gt_path.exists():
            print(f"  ⚠ {doc_id}: ground_truth/{doc_id}.json отсутствует — пропускаю")
            skipped += 1
            continue
        gt: GroundTruth = load_ground_truth(gt_path)

        meta_score = score_metadata(pred.metadata, gt.metadata)
        labs_score = None
        if gt.lab_results:
            labs_score = score_lab_results(pred.lab_results, gt.lab_results, synonyms_idx)

        summary_score = None
        if not skip_summary:
            summary_score = await score_summary(
                pred_summary=pred.summary,
                gt_summary=gt.summary_reference,
                gt_key_facts=gt.summary_key_facts,
                judge=judge,
                cache_dir=judge_cache_dir,
                api_key=api_key,
                base_url=base_url,
            )

        overall = _compute_overall(meta_score.overall, labs_score, summary_score)

        per_document.append(DocumentScore(
            doc_id=doc_id,
            metadata=meta_score,
            lab_results=labs_score,
            summary=summary_score,
            overall=overall,
        ))

        labs_brief = f"F1={labs_score.f1:.2f}" if labs_score else "n/a"
        if summary_score:
            tag = "cache" if summary_score.from_cache else "judge"
            sum_brief = f"sum={summary_score.normalized:.2f}[{tag}]"
        else:
            sum_brief = "sum=n/a"
        print(f"  {doc_id:<20} meta={meta_score.overall:.2f}  labs={labs_brief}  {sum_brief}  overall={overall:.2f}")

    manifest = load_manifest(dataset_dir / "manifest.yaml")
    aggregate = aggregate_run(per_document, manifest.documents)

    metrics = {
        "run_id": run_id,
        "scored_at": _now_iso(),
        "dataset_version": dataset_version,
        "model_id": model_id,
        "judge_model": None if skip_summary else judge.openrouter_slug,
        "skipped": skipped,
        "aggregate": aggregate.model_dump(mode="json"),
        "per_document": [d.model_dump(mode="json") for d in per_document],
    }
    (run_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report = render_run_report(
        run_id=run_id,
        model_id=model_id,
        judge_model=None if skip_summary else judge.openrouter_slug,
        dataset_version=dataset_version,
        aggregate=aggregate,
        per_document=per_document,
    )
    (run_dir / "report.md").write_text(report, encoding="utf-8")

    print()
    print(f"✅ Сохранено: {(run_dir / 'metrics.json').relative_to(REPO_ROOT)}")
    print(f"             {(run_dir / 'report.md').relative_to(REPO_ROOT)}")
    print()
    print(f"📈 overall={aggregate.overall_mean:.3f}  meta={aggregate.metadata_mean:.3f}", end="")
    if aggregate.lab_f1_mean is not None:
        print(f"  labs.F1={aggregate.lab_f1_mean:.3f}", end="")
    if aggregate.summary_mean is not None:
        print(f"  summary={aggregate.summary_mean:.3f}", end="")
    print()


def _compute_overall(meta: float, labs, summary) -> float:
    """Веса:
       - meta + labs + summary (есть всё) — 0.4 / 0.3 / 0.3
       - meta + labs (без summary)         — 0.6 / 0.4
       - meta + summary (без labs)         — 0.6 / 0.4
       - только meta                       — 1.0
    """
    has_labs = labs is not None
    has_sum = summary is not None
    labs_f1 = labs.f1 if has_labs else 0.0
    sum_norm = summary.normalized if has_sum else 0.0
    if has_labs and has_sum:
        return round(0.4 * meta + 0.3 * labs_f1 + 0.3 * sum_norm, 4)
    if has_labs:
        return round(0.6 * meta + 0.4 * labs_f1, 4)
    if has_sum:
        return round(0.6 * meta + 0.4 * sum_norm, 4)
    return round(meta, 4)


def cmd_prepare_document(args: argparse.Namespace) -> None:
    """Положить документ в датасет: скопировать файл, посчитать sha256,
    создать пустой ground_truth/<id>.json и напечатать YAML-блок для manifest."""
    src = Path(args.src).expanduser().resolve()
    if not src.exists():
        print(f"❌ Файл не найден: {src}")
        sys.exit(1)

    dataset_dir = BENCHMARK_ROOT / "datasets" / args.dataset
    if not dataset_dir.exists():
        print(f"❌ Датасет не найден: {dataset_dir}")
        sys.exit(1)

    docs_dir = dataset_dir / "documents"
    gt_dir = dataset_dir / "ground_truth"
    docs_dir.mkdir(parents=True, exist_ok=True)
    gt_dir.mkdir(parents=True, exist_ok=True)

    target_name = f"{args.id}{src.suffix.lower()}"
    target_path = docs_dir / target_name
    if target_path.exists() and not args.force:
        print(f"❌ Файл уже есть: {target_path}. Используйте --force чтобы перезаписать.")
        sys.exit(1)

    shutil.copy2(src, target_path)
    sha = sha256_of_file(target_path)

    gt_path = gt_dir / f"{args.id}.json"
    if gt_path.exists() and not args.force:
        print(f"⚠ ground_truth/{args.id}.json уже есть — НЕ перезаписываю. --force чтобы перезаписать.")
    else:
        template = {
            "doc_id": args.id,
            "source_file": target_name,
            "source_sha256": sha,
            "tags": {
                "document_type": args.type or "",
                "format": args.format,
                "specialty": args.specialty,
                "difficulty": args.difficulty,
            },
            "metadata": {
                "document_type": args.type or "",
                "document_subtype": None,
                "research_area": None,
                "specialties": [],
                "document_date": None,
                "patient_name": None,
                "medical_facility": None,
                "document_language": "ru",
                "confidence": None,
            },
            "summary_reference": "TODO: заполни эталонное summary",
            "summary_key_facts": ["TODO: список ключевых фактов"],
            "lab_results": [],
            "notes": args.notes,
        }
        gt_path.write_text(
            json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    yaml_entry = (
        f"  - id: {args.id}\n"
        f"    file: {target_name}\n"
        f"    sha256: \"{sha}\"\n"
        f"    format: {args.format}\n"
        f"    tags:\n"
        f"      document_type: \"{args.type or ''}\"\n"
    )
    if args.specialty:
        yaml_entry += f"      specialty: \"{args.specialty}\"\n"
    yaml_entry += f"      difficulty: {args.difficulty}\n"
    if args.notes:
        yaml_entry += f"    notes: \"{args.notes}\"\n"

    print(f"✅ Скопировано:   {target_path.relative_to(REPO_ROOT)}")
    print(f"✅ Ground truth:  {gt_path.relative_to(REPO_ROOT)}  (заполни TODO-поля)")
    print(f"📋 sha256:        {sha}")
    print()
    print("Добавь этот блок в manifest.yaml → documents:")
    print()
    print(yaml_entry, end="")


def cmd_compare(args: argparse.Namespace) -> None:
    """Сравнить несколько прогонов на одном датасете."""
    from benchmarks.document_analysis.src.metrics import RunAggregate

    runs_dir = BENCHMARK_ROOT / "runs"
    if not runs_dir.exists():
        print(f"❌ Папка {runs_dir} не существует — нечего сравнивать.")
        sys.exit(1)

    # Соберём список прогонов: либо явно из --run, либо все на --dataset
    if args.run:
        run_ids = list(args.run)
    else:
        run_ids = [p.name for p in sorted(runs_dir.iterdir()) if (p / "metrics.json").exists()]

    selected: list[dict] = []
    target_dataset: int | None = None
    for rid in run_ids:
        metrics_path = runs_dir / rid / "metrics.json"
        if not metrics_path.exists():
            print(f"⚠ {rid}: нет metrics.json — запустите `score` сначала. Пропускаю.")
            continue
        m = json.loads(metrics_path.read_text(encoding="utf-8"))
        dsv = m["dataset_version"]

        if args.dataset:
            want = int(args.dataset.lstrip("v"))
            if dsv != want:
                continue
        else:
            if target_dataset is None:
                target_dataset = dsv
            elif dsv != target_dataset:
                print(f"⚠ {rid}: dataset_version={dsv}, ожидался v{target_dataset}. Пропускаю.")
                continue

        target_dataset = dsv
        selected.append({
            "run_id": rid,
            "model_id": m["model_id"],
            "aggregate": RunAggregate.model_validate(m["aggregate"]),
        })

    if not selected:
        print("❌ Не нашлось ни одного прогона с metrics.json под условие.")
        sys.exit(1)

    report = render_compare_report(target_dataset or 0, selected)
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(report, encoding="utf-8")
        print(f"✅ Сохранено: {out_path}")
    else:
        print(report)


def cmd_sync_synonyms(args: argparse.Namespace) -> None:
    """Выгрузить таблицу analyte_synonyms из Postgres в локальный JSON-кэш."""
    dsn = args.dsn or os.environ.get("BENCHMARK_DATABASE_URL")
    if not dsn:
        print("❌ Нужен --dsn или BENCHMARK_DATABASE_URL в окружении.")
        print("   Пример (локальный Postgres из docker-compose):")
        print("     export BENCHMARK_DATABASE_URL=\\")
        print("       'postgresql://medhistory_user:<password>@localhost:5432/medhistory'")
        sys.exit(1)

    # asyncpg-style URL из docker-compose.yml psycopg не понимает.
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")

    print("📥 Запрашиваю synonyms из БД...")
    try:
        data = fetch_index_from_db(dsn)
    except Exception as e:
        print(f"❌ Не удалось получить данные: {type(e).__name__}: {e}")
        sys.exit(1)

    cache_path = BENCHMARK_ROOT / ".cache" / "synonyms.json"
    save_cache(data, cache_path)

    stats = data["stats"]
    print(f"✅ Сохранено: {cache_path.relative_to(REPO_ROOT)}")
    print(f"   Pairs (synonym × unit): {stats['rows']}")
    print(f"   Unique synonyms:        {stats['unique_synonyms']}")
    print(f"   Canonicals:             {stats['canonicals']}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Проверить целостность датасета: каждому manifest.documents соответствует
    реальный файл с правильным sha256 и есть ground_truth/<id>.json."""
    dataset_dir = BENCHMARK_ROOT / "datasets" / args.dataset
    manifest = load_manifest(dataset_dir / "manifest.yaml")

    if not manifest.documents:
        print("⚠️  manifest.documents пуст — нечего валидировать.")
        return

    errors: list[str] = []
    for doc in manifest.documents:
        doc_path = dataset_dir / "documents" / doc.file
        gt_path = dataset_dir / "ground_truth" / f"{doc.id}.json"

        if not doc_path.exists():
            errors.append(f"{doc.id}: файл документа не найден ({doc.file})")
            continue

        actual_sha = sha256_of_file(doc_path)
        if actual_sha != doc.sha256:
            errors.append(
                f"{doc.id}: sha256 mismatch (manifest={doc.sha256[:10]}.., file={actual_sha[:10]}..)"
            )

        if not gt_path.exists():
            errors.append(f"{doc.id}: ground_truth/{doc.id}.json отсутствует")

    if errors:
        print(f"❌ Найдено {len(errors)} проблем:")
        for e in errors:
            print(f"   - {e}")
        sys.exit(1)

    print(f"✅ Датасет v{manifest.version} валиден ({len(manifest.documents)} документов).")


def main() -> None:
    parser = argparse.ArgumentParser(prog="benchmark-doc-analysis")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Запустить extraction-pipeline по датасету")
    p_run.add_argument("--dataset", default="v1", help="Версия датасета, напр. v1")
    p_run.add_argument("--model", required=True, help="id модели из models.yaml")
    p_run.add_argument("--doc", help="(опц.) id одного документа для прогона")
    p_run.set_defaults(func=cmd_run)

    p_val = sub.add_parser("validate-dataset", help="Проверить целостность датасета")
    p_val.add_argument("--dataset", default="v1")
    p_val.set_defaults(func=cmd_validate)

    p_score = sub.add_parser("score", help="Посчитать метрики для существующего прогона")
    p_score.add_argument("--run", required=True, help="id прогона (имя папки в runs/)")
    p_score.add_argument(
        "--no-summary",
        action="store_true",
        help="Не вызывать LLM-as-judge для summary (быстро, без расхода на API)",
    )
    p_score.set_defaults(func=cmd_score)

    p_sync = sub.add_parser("sync-synonyms", help="Выгрузить analyte_synonyms из Postgres в кэш")
    p_sync.add_argument("--dsn", help="DSN Postgres. Если не задан — берётся из BENCHMARK_DATABASE_URL")
    p_sync.set_defaults(func=cmd_sync_synonyms)

    p_prep = sub.add_parser(
        "prepare-document",
        help="Положить документ в датасет (копирует файл, считает sha256, создаёт шаблон ground_truth)",
    )
    p_prep.add_argument("--src", required=True, help="Путь к исходному файлу документа")
    p_prep.add_argument("--id", required=True, help="ID документа в датасете (напр. doc_001)")
    p_prep.add_argument("--dataset", default="v1")
    p_prep.add_argument(
        "--format", required=True,
        choices=["pdf_text", "pdf_scan", "image_lab_printed", "photo_handwritten", "photo_printed", "docx", "other"],
    )
    p_prep.add_argument("--type", help="document_type (напр. \"Результаты анализа\")")
    p_prep.add_argument("--specialty")
    p_prep.add_argument("--difficulty", default="medium", choices=["easy", "medium", "hard"])
    p_prep.add_argument("--notes")
    p_prep.add_argument("--force", action="store_true", help="Перезаписать существующий файл/GT")
    p_prep.set_defaults(func=cmd_prepare_document)

    p_cmp = sub.add_parser("compare", help="Сравнить несколько прогонов на одном датасете")
    p_cmp.add_argument("--dataset", help="Версия датасета (v1). Если не задана — берётся из первого run-а.")
    p_cmp.add_argument("--run", action="append", help="id прогона (можно несколько раз)")
    p_cmp.add_argument("--output", help="Куда сохранить отчёт. По умолчанию — stdout.")
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
