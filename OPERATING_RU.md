# Process Architect — эксплуатация

Руководство по запуску BitGN ECOM1 и подготовке среды для перехода dev -> prod. Данный документ определяет базовые процессы эксплуатации.

Основная точка входа:

```bash
uv run python -m orchestrator.main [task-filter ...] [flags]
```

Предварительная настройка перед первым запуском:

```bash
uv sync
export BITGN_API_KEY=...
```

## 1. Управление ветками (Branches)

* Для работы в dev-окружении: переключитесь на ветку `postmortem-dev`.
* Для выполнения перехода dev -> prod (через `world_refresh`): используйте ветку `postmortem-dev` и обратитесь к разделу «Dev -> Prod» данного документа.
* Для оценки итогового prod-состояния: переключитесь на ветку `postmortem-prod`.

```bash
git switch postmortem-dev
git switch postmortem-prod
```

## 2. Системные требования

* Python версии `>=3.14` и пакетный менеджер `uv`.
* Claude Code CLI: исполняемый файл `claude` должен быть доступен в `PATH` или явно задан через переменную окружения `CLAUDE_BIN=/path/to/claude`.
* Предварительная авторизация Claude CLI в рабочей среде пользователя.
* Доступ к BitGN API: сетевая доступность до harness и наличие токена `BITGN_API_KEY`.
* Указание целевого benchmark для prod/dev окружения через параметр `--benchmark`.

## 3. Запуск

Стандартный dev-запуск в ветке `postmortem-dev`:

```bash
uv run python -m orchestrator.main \
  --benchmark bitgn/ecom1-dev \
  --concurrency 1
```

Запуск отдельных dev-задач:

```bash
uv run python -m orchestrator.main t01 t05 \
  --benchmark bitgn/ecom1-dev \
  --concurrency 1
```

Полный prod-запуск в ветке `postmortem-prod`:

```bash
uv run python -m orchestrator.main \
  --benchmark bitgn/ecom1-prod \
  --concurrency 15 \
  --pa-llm-concurrency 0
```

Расширенные режимы PA (Process Architect) по умолчанию отключены: `--pa-fix`, `--refresh`, `--world-refresh` и `--world-create` требуют явной активации. Параметр `--pa-llm-concurrency 1` по умолчанию определяет только вместимость очереди PA; если вышеуказанные режимы не активированы, PA не вносит изменений в процессы. Полное отключение PA осуществляется флагом: `--pa-llm-concurrency 0`.

Активация режима PA-fix (эволюция) после неудачных испытаний (trial):

```bash
uv run python -m orchestrator.main \
  --benchmark bitgn/ecom1-dev \
  --concurrency 1 \
  --pa-fix
```

Позиционные аргументы `task-filter` применяются как substring-фильтры по `task_id`. Поскольку harness раскрывает `task_id` только после инициализации `start_trial`, нерелевантные trial запускаются и закрываются через `OUTCOME_ERR_INTERNAL`.

## 4. Переход Dev -> Prod

Цель перехода заключается в адаптации процессов к prod runtime без использования prod-задач и их результатов в качестве обучающей выборки. Подготовленный профиль prod executor располагается в директории `.tasks/task-005/executor_core_prod/v0018/`.

1. Скопировать конфигурацию prod `executor_core`, если она отсутствует в текущей ветке.
```bash
test -d instructions/units/executor_core/v0018 || \
  cp -a .tasks/task-005/executor_core_prod/v0018 \
    instructions/units/executor_core/v0018
```


2. Инициировать carrier-run для выполнения `world_refresh`.
```bash
BITGN_API_KEY=... \
uv run python -m orchestrator.main t001 \
  --benchmark bitgn/ecom1-prod \
  --concurrency 1 \
  --pa-llm-concurrency 1 \
  --world-refresh \
  --stale-resolution wait_for_refresh
```



## 5. Основные параметры

CLI-флаги имеют приоритет над переменными окружения и значениями по умолчанию, заданными в `orchestrator/config.py`.

Параметры выполнения / Executor:

| Переменная / Флаг | По умолчанию | Описание |
| --- | --- | --- |
| `BITGN_API_KEY` / `--bitgn-api-key` | пусто | API-ключ для инициализации `start_run`. |
| `BENCHMARK_ID`, `BENCH_ID` / `--benchmark` | `bitgn/ecom1-dev` | Идентификатор benchmark (обычно `bitgn/ecom1-dev` или `bitgn/ecom1-prod`). |
| `RUN_NAME` / `--run-name` | `@GaricY Process Architect postmortem` | Наименование run в harness и формируемых отчетах. |
| `RUNS_ROOT` / `--runs-root` | `../.runs/ecom` | Корневая директория для локальных run-артефактов. |
| `CONCURRENCY` / `--concurrency` | `1` | Количество параллельных процессов trial worker. |
| `CLAUDE_BIN` / `--claude-bin` | `claude` | Путь к исполняемому файлу Claude CLI. |
| `CLAUDE_MODEL` / `--model` | `claude-sonnet-4-6` | Используемая модель для Executor. |
| `CLAUDE_REASONING_EFFORT` / `--effort` | `medium` | Уровень детализации Reasoning для Executor: `low`, `medium`, `high`, `xhigh`, `max`. |
| `CLAUDE_MAX_TURNS` / `--max-turns` | `40` | Ограничение количества итераций (turns) для Executor. |

Параметры Process Architect (PA):

| Переменная / Флаг | По умолчанию | Описание |
| --- | --- | --- |
| `PA_LLM_CONCURRENCY` / `--pa-llm-concurrency` | `1` | Количество параллельных LLM-сессий PA; значение `0` полностью отключает PA. |
| `PA_FIX_ENABLED` / `--pa-fix`, `--no-pa-fix` | `false` | Разрешает выполнение `failure_fix` / `fix_blind` после неудачного trial. |
| `REFRESH_ENABLED` / `--refresh`, `--no-refresh` | `false` | Разрешает per-unit обновление (refresh) при возникновении dependency drift. |
| `WORLD_REFRESH_ENABLED` / `--world-refresh`, `--no-world-refresh` | `false` | Разрешает world-level обновление на основе drift baseline. |
| `WORLD_CREATE_ENABLED` / `--world-create`, `--no-world-create` | `false` | Инициирует `world_create` вместо `world_refresh` для создания нового world-baseline из текущего dump или обработки сильного drift. |
| `STALE_RESOLUTION` / `--stale-resolution` | `latest_async_refresh` | Действие при обнаружении устаревших (stale) зависимостей: `latest_async_refresh` или `wait_for_refresh`. |
| `PA_APPLY` / `--pa-apply`, `--no-pa-apply` | `true` | Применение валидных решений PA; `--no-pa-apply` переводит в режим dry-run (без применения). |
| `PA_CLAUDE_MODEL` / `--process-architect-model` | `claude-opus-4-8` | Используемая модель для PA. |
| `PA_CLAUDE_REASONING_EFFORT` / `--process-architect-effort` | `xhigh` | Уровень детализации Reasoning для PA. |

## 6. Дополнительные параметры

Дополнительные настройки для выполнения / Executor:

| Переменная / Флаг | По умолчанию | Описание |
| --- | --- | --- |
| `BITGN_HOST`, `BENCHMARK_HOST` / `--host` | `https://api.bitgn.com` | Сетевой адрес BitGN harness. |
| `--no-submit` | выключено | Режим отладки: сохраняет run в открытом состоянии после завершения trial. |
| `--limit` | пусто | Ограничение запуска первыми N trial из выбранного benchmark. |
| `TRIAL_START_INTERVAL_SEC` / `--trial-start-interval` | `2` | Интервал (в секундах) между инициализацией `start_trial`; значение `0` отключает задержку. |
| `--trial-timeout` | `1800` | Общий таймаут сессии Claude CLI на один trial (в секундах). |
| `--snippet-timeout` | `180` | Таймаут выполнения одного сниппета `execute_python` (в секундах). |
| `--internal-error-retries` | `5` | Количество попыток повторного выполнения Executor при отсутствии `answer.json` или возникновении `OUTCOME_ERR_INTERNAL`. |
| `DUMP_SQL_ROWS` / `--dump-sql-rows` | `0` | Лимит строк для дампа пользовательских таблиц в `dump_sql/`; значение `0` отключает дамп. |
| `BLIND_EMULATION` / `--blind-emulation`, `--no-blind-emulation` | `false` | DEV-эмуляция политики blind policy: оценки (score) и подсказки (hints) скрыты от agent stack, фактические оценки записываются в директорию `<run_id>-score/`. |

Дополнительные настройки для PA:

| Переменная / Флаг | По умолчанию | Описание |
| --- | --- | --- |
| `PA_MAX_TURNS` / `--process-architect-max-turns` | `0` | Ограничение количества итераций для PA; `0` означает отсутствие `--max-turns` (применяется только таймаут). |
| `PROCESS_ARCHITECT_TIMEOUT_SEC` / `--process-architect-timeout` | `1200` | Таймаут для non-world режимов PA: `refresh`, `failure_fix`, `fix_blind`, conflict retry. |
| `PROCESS_ARCHITECT_WORLD_TIMEOUT_SEC` / `--process-architect-world-timeout` | `7200` | Таймаут для режимов `world_refresh` / `world_create`. |
| `PA_CONFLICT_MODE` / `--pa-conflict-mode`, `--no-pa-conflict-mode` | `true` | Выполняет rebase решения PA, если базовая версия (base version) устарела на момент применения. |
| `PA_CONFLICT_MAX_RETRIES` / `--pa-conflict-max-retries` | `1` | Максимальное количество попыток выполнения conflict rebase. |
| `--process-architect`, `--no-process-architect` | включено | Устаревший параметр (Legacy gate), активирующий только режимы PA-fix; не включает `refresh` или `world_refresh`. |
| `--wait-process-architect` | выключено | Блокировка продолжения выполнения run до завершения PA failure-fix (используется в исключительных случаях). |

## 7. Структура директории `task_dir`

Для каждого trial создается изолированная директория по следующему шаблону:

```text
<RUNS_ROOT>/<run_id>/<NNNN>-<task_id>-<trial_id>/
```

Ключевые файлы и директории:

| Путь | Назначение |
| --- | --- |
| `task.md` | Текст задачи и базовая инструкция для Executor. |
| `CLAUDE.md` | Скомпилированная версия `executor_core`. |
| `business_processes/*.md` | Скомпилированные версии бизнес-процессов. |
| `vault/` | Дамп актуальных файлов `/docs`, `/bin`, `AGENTS.MD`, `README.md` и связанных ресурсов. |
| `bin-help/` | Справка (`--help`) для утилит в `/bin/*` и файл `sqlite_schema.txt`. |
| `tree.md` | Снимок файлового дерева виртуальной машины на момент старта trial. |
| `attention/` | Данные по drift, карты релокации (relocation map) и предупреждения для устаревших зависимостей. |
| `scratchpad.json` | Промежуточный рабочий файл (scratchpad) Executor. |
| `state.json` | Рабочее состояние, сохраняемое между выполнением `execute_python` сниппетов. |
| `answer.json` | Итоговый ответ системы: `message`, `outcome`, `refs`. |
| `result.json` | Данные о выполнении: outcome, score, turns, cost, тайминги, MCP calls. |
| `runtime_prelude.py` | Вспомогательный runtime-код, доступный для выполнения сниппетов. |
| `dump_sql/` | SQL-дамп (генерируется при условии `--dump-sql-rows > 0`). |
| `.logs/transcript.jsonl` | Stream-формат транскрипта выполнения Claude CLI. |
| `.logs/claude-stderr.log` | Лог ошибок (stderr) Claude CLI (при наличии). |
| `.logs/mcp-tool-calls.jsonl` | Полный журнал MCP-вызовов, инициированных Executor. |
| `.logs/python/` | Журнал выполнения сниппетов `execute_python` и их результаты. |
| `.logs/executor_actions.md` | Аудит действий Executor в человекочитаемом формате. |
| `.logs/instruction-selection.json` | Журнал выбора версий юнитов компонентом Resolver и зафиксированный drift. |
| `.logs/pre-bootstrap-manifest.json` | Манифест файлов, скопированных в `vault/`, и правила их обработки. |
| `.logs/bin-help-manifest.json` | Хэш-суммы и состав содержимого директории `bin-help/`. |

Для аналитики и сравнения прогонов рекомендуется использовать `.logs/instruction-selection.json` вместо `task.md`, так как BitGN может рандомизировать текст задачи между различными run.

## 8. Артефакты выполнения (run)

В корневой директории run генерируются следующие артефакты:

| Путь | Назначение |
| --- | --- |
| `run.json` | Локальный `run_id`, системный `harness_run_id`, benchmark, идентификаторы trial. Записывается немедленно после `start_run`. |
| `console.log` | Полный дамп стандартного вывода и потока ошибок (stdout/stderr) оркестратора. |
| `summary.json` | Итоговые результаты выполнения в машиночитаемом формате. |
| `report.md` | Подробный отчет для анализа (score, outcome, costs, timings). |
| `report_PA.md` | Агрегированный отчет по задачам PA (формируется, если PA был запущен). |
| `<task_dir>/...` | Артефакты выполнения отдельных trial. |
| `<task_dir>-process-architect*/` | Рабочие директории (workdir) задач PA. |

Ключевые метрики в отчете `report.md`:

| Поле | Значение |
| --- | --- |
| `wall-clock` | Фактическая общая длительность выполнения run. |
| `cpu-sum` | Суммарное время работы Executor по всем trial. |
| `trial-sum` | Суммарное время от `start_trial` до `end_trial` (приближено к organizer metric). |
| `boot-sum` | Время, затраченное на подготовку директории `task_dir`. |
| `executor: turns/mcp/cost` | Объем ресурсов, затраченных Executor. |
| `process architect: jobs/turns/cost` | Объем ресурсов, затраченных PA. |

При включенной слепой эмуляции (blind-emulation) параллельно создается директория `<run_id>-score/`, содержащая фактические оценки для ручного анализа. Основной процесс выполнения при этом сохраняет свою исходную конфигурацию (blind-shaped).
