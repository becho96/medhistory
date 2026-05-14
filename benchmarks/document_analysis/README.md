# Document Analysis Benchmark

Бенчмарк качества первичного анализа документов в MedHistory: оценивает извлечение
метаданных, summary и лабораторных результатов на версионированной тестовой выборке
с ground truth.

Запускает **тот же** prod-pipeline (`backend/app/services/ai_service.py`) с подменяемой
LLM, поэтому показывает реальное поведение системы, а не упрощённую модель.

## Когда использовать

- сравнить точность извлечения у двух моделей перед сменой prod-модели;
- задать baseline и отслеживать регрессии при изменении промптов;
- проверить, как pipeline справляется с разными форматами (PDF, фото рукописных, сканы).

## Быстрый старт

```bash
# 1. Один раз: окружение
cd benchmarks/document_analysis
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Один раз (и при изменениях прод-БД): кэш канонизации lab-имён
#    DSN можно взять из docker-compose backend контейнера
BENCHMARK_DATABASE_URL='postgresql://medhistory_user:<pw>@localhost:5432/medhistory' \
  python -m benchmarks.document_analysis.src.cli sync-synonyms

# 3. Прогон + метрики (из корня репозитория)
cd ../..
source benchmarks/document_analysis/venv/bin/activate
python -m benchmarks.document_analysis.src.cli run   --dataset v1 --model gemini-2.5-flash
python -m benchmarks.document_analysis.src.cli score --run <run_id>

# 4. Сравнить несколько моделей на одном датасете
python -m benchmarks.document_analysis.src.cli compare --dataset v1
```

`OPENROUTER_API_KEY` подгружается автоматически из `.env.local` в корне репозитория
(через `python-dotenv`). Остальные поля Settings подставляются заглушками — pipeline
извлечения не обращается ни к Postgres, ни к MinIO.

## Структура

```
benchmarks/document_analysis/
├── models.yaml                  Реестр extraction-моделей + фиксированный judge
├── requirements.txt             Зависимости (pydantic, httpx, psycopg, reportlab, …)
├── datasets/v<N>/               Версия датасета — иммутабельна после фиксации
│   ├── manifest.yaml            Описание версии, категории, список документов
│   ├── documents/               Сами файлы (gitignored — PII)
│   └── ground_truth/<id>.json   Эталонная разметка на каждый документ
├── runs/<ts>_<model>_v<N>/      Артефакты одного прогона (gitignored)
│   ├── run_meta.json            Модель, prompt_versions (sha), git_commit
│   ├── predictions/<id>.json    Сырой ответ extraction-pipeline
│   ├── metrics.json             Aggregate + per-document scores
│   └── report.md                Human-readable отчёт
├── .cache/                      Кэши: synonyms.json и judge-ответы (gitignored)
├── src/
│   ├── schema.py                Pydantic: GroundTruth, Prediction, RunMeta, …
│   ├── runner.py                BenchmarkAIService — наследник AIService
│   ├── synonyms.py              Канонизация (analyte_standards + analyte_synonyms)
│   ├── cli.py                   Все команды
│   └── metrics/                 Метрики и aggregate + render отчётов
└── tools/                       Утилиты (генератор синтетических PDF)
```

## CLI

| Команда | Назначение |
|---------|------------|
| `run --dataset v1 --model <id>` | Прогон extraction-pipeline по датасету. Артефакты в `runs/<ts>_<model>_v<N>/predictions/`. |
| `score --run <run_id>` | Посчитать метрики для прогона. Создаёт `metrics.json` + `report.md`. Флаг `--no-summary` пропускает LLM-judge. |
| `compare --dataset v1` | Markdown-таблица всех прогонов на v1. Альтернатива: `--run id1 --run id2 …`. `--output file.md` для файла. |
| `validate-dataset --dataset v1` | Проверить sha256 файлов и наличие `ground_truth/<id>.json`. |
| `sync-synonyms` | Выгрузить `analyte_synonyms` из Postgres в `.cache/synonyms.json`. Источник DSN — `--dsn` или `BENCHMARK_DATABASE_URL`. |
| `prepare-document --src <path> --id <id> --format <fmt> …` | Положить документ в датасет: копирует файл, считает sha256, создаёт шаблон ground_truth, печатает YAML-блок для manifest. |

## Метрики

### Metadata (per-document `meta`)

Поля и метод сравнения:
- `document_type`, `document_subtype`, `research_area`, `document_language`, `document_date` — **exact match** (1/0).
- `patient_name`, `medical_facility` — **fuzzy** (`difflib.SequenceMatcher`, порог 0.85).
- `specialties` — **set-based F1** на нормализованных строках.

Overall — взвешенная сумма по полям с непустым GT:

| поле | вес |
|------|-----|
| document_type | 1.0 |
| document_subtype, specialties | 0.6 |
| document_date, patient_name, medical_facility, research_area | 0.4 |
| document_language | 0.2 |

Поля с пустым GT не штрафуются.

### Lab results (per-document `labs`)

1. Канонизация имён через индекс `synonyms.json`: ключ `(synonym_lower, unit_lower)` → `canonical_name`. Если по паре нет — fallback по уникальному имени.
2. GT-имена берутся из `analyte_canonical` (или канонизируются `test_name`); `aliases[]` расширяют индекс GT.
3. Set-метрики на канонических именах: **precision / recall / F1**.
4. Для matched пар:
   - `value_accuracy` — numeric tolerance 5 % (`4.50` ≈ `4.51`), иначе string exact;
   - `unit_accuracy` — нормализованное точное совпадение;
   - `flag_accuracy` — exact (`L|N|H|A`).

### Summary (per-document `sum`)

LLM-as-judge — фиксированная модель из `models.yaml` (`anthropic/claude-opus-4.7`,
temperature 0). Возвращает три шкалы 0..5:

- `factuality` — соответствие фактам эталона;
- `completeness` — какая доля `summary_key_facts` раскрыта;
- `hallucination_freedom` — насколько свободно от выдумок.

`normalized = (factuality + completeness + hallucination_freedom) / 15`. Дополнительно
возвращается `per_fact_coverage` (массив того же размера, что `summary_key_facts`).

Ответы судьи кэшируются в `.cache/judge/<sha256>.json` по `(pred, gt, facts, judge_model)`
— повторный `score` не оплачивает уже посчитанное.

### Overall (per-document)

| Что есть | overall = |
|----------|-----------|
| meta + labs + summary | `0.4·meta + 0.3·labs.F1 + 0.3·summary.normalized` |
| meta + labs (без summary) | `0.6·meta + 0.4·labs.F1` |
| meta + summary (без labs) | `0.6·meta + 0.4·summary.normalized` |
| только meta | `meta` |

## Версионирование датасета

Каждая `datasets/vN/` после фиксации — **иммутабельна**. Любое существенное изменение
состава, добавление новой категории или правка ground truth → новая `vN+1`.

В каждом манифесте:
- `version`, `created_at`, `status` (`in_progress` | `frozen`);
- `description` — что вошло, для каких задач;
- `changes_from_previous` — что отличается от предыдущей версии;
- `categories` — справочное распределение целевого покрытия (`target_count`);
- `documents` — фактический список с `sha256`, `format`, `tags`.

`run` сверяет sha256 файла с записью в манифесте: если документ изменили без bump-а
версии, прогон пропускает этот документ — baseline не сломается из-за молчаливой подмены.

## Добавление новой модели

1. Открыть [models.yaml](models.yaml), добавить запись в `extraction_models`:

   ```yaml
   - id: <короткое-имя>
     openrouter_slug: <provider>/<model>
     temperature: 0.1
     notes: "<когда добавили / зачем>"
   ```

2. Запустить прогон: `... run --dataset v1 --model <короткое-имя>`.

Если модель упадёт при первом вызове (например, неправильный slug у OpenRouter) — `run`
поймает это: `analyze_document` вернёт `document_type="неизвестно"` и `Prediction.error`
будет заполнен. Корректируем slug и перезапускаем.

**Judge** меняется отдельно (секция `judge` в `models.yaml`). Делать это надо
сознательно: разные судьи дают несравнимые `summary.normalized` между прогонами.

## Добавление нового документа

```bash
# 1. helper кладёт файл в датасет и печатает YAML-блок
python -m benchmarks.document_analysis.src.cli prepare-document \
  --src ~/Downloads/cbc.pdf \
  --id doc_005_cbc \
  --format pdf_text \
  --type "Результаты анализа" \
  --specialty "Терапия" \
  --difficulty easy

# 2. Скопировать напечатанный блок в datasets/v1/manifest.yaml → documents:
# 3. Открыть datasets/v1/ground_truth/doc_005_cbc.json и заполнить TODO
# 4. python -m benchmarks.document_analysis.src.cli validate-dataset --dataset v1
```

Поддерживаемые `--format`: `pdf_text`, `pdf_scan`, `image_lab_printed`,
`photo_handwritten`, `photo_printed`, `docx`, `other`.

### Правила разметки ground truth

1. **Прочитать оригинал документа ПОЛНОСТЬЮ** перед заполнением
   `summary_reference` и `summary_key_facts`. Это самый частый источник
   ошибок: при разметке по первым строкам легко пропустить факты в
   концовке (назначения лекарств, лабораторные значения в тексте, направления).
2. `summary_key_facts` — атомарные утверждения, каждое должно быть
   проверяемо `true`/`false` независимо. Включают: пациент, дата,
   учреждение, диагноз, ВСЕ упомянутые показатели и назначения.
3. `summary_reference` явно содержит то же самое в связном виде.
4. **LLM-судья ≠ источник истины.** Если судья помечает факт как
   «галлюцинацию», но он реально есть в оригинале — править надо GT,
   а не оправдывать судью. На спорных кейсах сверяйся с исходным
   документом, не доверяй вердикту слепо.
5. Для `lab_results`: заполняется ТОЛЬКО для документов
   `document_type="Результаты анализа"`. Pipeline вызывает lab extraction
   только для этого типа — даже если в записи приёма врача упомянуты
   числовые показатели, в `lab_results` GT они не должны попадать (попадут
   в `summary_key_facts`).

## Источник данных канонизации

`analyte_standards` + `analyte_synonyms` берутся из локального Postgres
(после ручной синхронизации с прода через `pg_dump`). Чтобы пересинхронизировать:

```bash
TS=$(date +%Y%m%d_%H%M%S)
ssh -i ~/.ssh/medhistory_deploy root@194.87.140.190 \
  "docker exec medhistory-postgres-1 pg_dump -U medhistory_user medhistory \
     --data-only --column-inserts \
     --table=analyte_categories --table=analyte_standards --table=analyte_synonyms \
     > /tmp/prod_synonyms.sql"
scp -i ~/.ssh/medhistory_deploy root@194.87.140.190:/tmp/prod_synonyms.sql \
    /tmp/prod_synonyms_${TS}.sql

# Затем на локальной БД: backup → DELETE → подгрузить дамп → sync-synonyms бенчмарка
```

## Известные ограничения

- **Отсканированные PDF без текстового слоя** — pipeline сейчас падает с
  `требуется OCR`. Бенчмарк фиксирует это как `Prediction.error` и считает документ
  неуспешным. OCR-стадия — отдельная задача.
- **Канонизация без unit** — если в GT и pred оба не указали unit, fallback работает
  только при единственном кандидате. Иначе матч не пройдёт (см. `synonyms.py`).
- **PII** — `documents/`, `runs/`, `.cache/judge/` находятся в `.gitignore`.
  Не использовать реальные документы пациентов без обезличивания.
- **prepare-document не правит manifest.yaml** — печатает YAML-блок для копи-пасты.
  Это намеренно: PyYAML стирает комментарии при перезаписи.

## Артефакты прогона

`runs/<ts>_<model>_v<N>/` содержит всё, что нужно для воспроизводимости:

- `run_meta.json` — точный slug модели, temperature, sha-промптов
  (`metadata_prompt`, `lab_prompt`), git-commit backend, время старта/завершения;
- `predictions/<id>.json` — что вернул pipeline (metadata, summary, lab_results,
  error если был);
- `metrics.json` — aggregate + per-document scores;
- `report.md` — таблица для глаза.
