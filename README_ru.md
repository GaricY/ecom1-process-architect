# ecom1-process-architect


Автономный агент для соревнования **BITGN Agent Challenge: E-commerce
(ECOM1)**. Подключается к BitGN API и решает задачи цифрового магазина в
детерминированной симуляции — product discovery, корзина/checkout, сбои
платежей, fraud-границы, возвраты, рефанды, замены, поддержка — и оценивается
по **наблюдаемым действиям, изменениям состояния и соблюдению политик**, а не по
красоте текста.

## Идея

Я больше 15 лет занимался внедрением ERP-систем, и любой проект начинается
одинаково. С чего? ~~Мы садимся писать код.~~ Мы **составляем карту
бизнес-процессов.** Код приходит позже; это лишь один из способов выразить
процесс, который уже существует — в policy book, в головах людей, в том, как
бизнес реально работает.

Этот агент построен на той же интуиции: карта бизнес-процессов — первична, как
первоклассный артефакт, — и к ней применяется та же дисциплина, что и к кодовой
базе. Потому что у проектирования бизнес-процессов и разработки софта много
общего: и то, и другое превращает размытые требования реального мира в точные,
композируемые, тестируемые правила, и то, и другое гниёт, если растёт одним
вечно разбухающим монолитом, который страшно трогать.

Поэтому главная ставка простая: **относиться к инструкциям агента как к коду и
применять к ним инженерные практики.**

И вторая ставка, вытекающая из первой: **не зашивать домен в механику — пусть
агент выстроит его сам.** Оркестратор, resolver, версионированный стор, контур PA
— ни одна из этих частей не знает ничего про e-commerce. Всё доменное знание
живёт в business-process юнитах, которые агент выводит из живого мира сам
(`world_create` / `world_refresh`). Наведи ту же машину на другой мир — и она
построит новую карту процессов: домен — это работа агента, а не фреймворка.

Что это значит конкретно:

- **Инструкции — модульные, версионируемые, immutable юниты.** Operating manual
  Executor'а — это не один гигантский промпт, а набор business-process (BP)
  юнитов (identity & auth, checkout, скидки, fraud review, возвраты, гигиена
  refs, …); каждый — immutable `vNNNN/` со своим content, manifest и **явно
  объявленными зависимостями** от мира (конкретные docs, `--help` инструментов,
  схема БД). Это читается как небольшая кодовая база, а не стена текста.
- **«Мир» — это upstream, от которого зависят юниты.** Docs, инструменты и
  политики организатора — поверхность зависимостей. Когда они дрейфуют, юниты,
  которые их пинили, становятся *stale* — ровно как bump зависимости, ломающий
  модуль, — и resolver выбирает под каждую задачу ту версию, чьи зависимости всё
  ещё совпадают с живым миром.
- **Process Architect (PA) — инженер в контуре.** Он выпускает новые версии по
  обратной связи так же, как разработчик реагирует на CI:
  - провал трайла (score грейдера) → `failure_fix`: чинит юнит за провалом —
    багфикс по упавшему тесту;
  - мир поплыл → `world_refresh`: инкрементальный рефакторинг затронутых BP (или
    `refresh` для одного stale-юнита);
  - совсем новый или радикально иной мир (например, `dev → prod`) →
    `world_create`: пересборка всего BP-набора с нуля из текущего дампа мира.
    Стартовый BP-набор был собран именно так.
- **Всё — аудируемая история.** Immutable `vNNNN/` с диффами и changelog'ами,
  baseline-снапшот «мира, каким мы его в последний раз приняли», и реестр
  активных юнитов — git-подобный след для собственных инструкций агента.

Выигрыш: вместо одного статичного промпта, который никто не может безопасно
тронуть, у агента — модульный, версионируемый, самоэволюционирующий operating
manual, и он адаптируется к меняющемуся бенчмарку так же, как хорошо
спроектированный софт адаптируется к меняющимся требованиям.

## Как это работает

- **Executor** — крутится как `claude -p` в per-trial директории; единственный
  runtime-инструмент — MCP-сервер `mcp__ecom-python__execute_python` (пишет
  питон-сниппеты, они исполняются в VM задачи и завершаются вызовом
  `submit_and_exit(...)`). Его промпт (`CLAUDE.md` + `business_processes/*.md`)
  **рендерит resolver под каждый trial** из версионированного стора
  `instructions/units/<id>/vNNNN/` — это не статичный файл, поддерживаемый
  руками.
- **Process Architect (PA)** — между трайлами эволюционирует юниты инструкций,
  выпуская новую immutable `vNNNN/`. Режимы:
  - `failure_fix` / `fix_blind` — когда доступен score трайла (или, под blind
    eval, Executor-трейс), разбирает каждый провал и чинит виновный(ые) юнит(ы).
  - `world_refresh` — когда foundational world-файлы поплыли vs последний
    baseline, **инкрементально** рефрешит существующие BP, добавляет новые под
    новые домены и продвигает baseline.
  - `world_create` — тот же триггер дрейфа, но **пересобирает весь BP-набор** из
    текущего дампа мира (существующие юниты — лишь черновики / якоря именования).
    Для совсем нового или радикально иного мира — и именно так был собран
    стартовый BP-набор.
  - `refresh` — один юнит, у которого поплыла per-unit зависимость.

  Все **content-режимы PA по умолчанию выключены** (см. [Конфигурация](#конфигурация)):
  механизм остаётся включён, чтобы дрейф всё равно всплывал у Executor'а, но
  агент не переписывает себя сам, пока его об этом не попросят.
- **Orchestrator** — детерминированный Python, гоняющий harness-loop BitGN
  (`get_benchmark` → `start_run` → per-trial `start_trial`/`end_trial` →
  `submit_run` → `get_run` за скорами), дампит живой мир (`/docs`, `/bin`,
  каждый `AGENTS.md`/`README.md`, `--help` инструментов, SQL-схему) в каждую
  trial-директорию, резолвит инструкции, спавнит Executor и PA, пишет отчёты.

## Быстрый старт

```bash
uv sync                                    # собрать venv (через uv)
echo 'BITGN_API_KEY=...' > .env            # gitignored
set -a; source .env; set +a

# один таск, БЕЗ публикации в лидерборд:
CONCURRENCY=1 uv run python -m orchestrator.main t01 --no-submit
# или: make smoke
```

Дефолтный бенчмарк — `bitgn/ecom1-dev` (открытый, со скорами). Subset-прогон всё
равно `start_trial`-ит **каждый** trial (харнес раскрывает `task_id` только
тогда) и **по умолчанию сабмитит в лидерборд** — для smoke без публикации
передавайте `--no-submit`. `make run` гонит весь бенчмарк; `make task
TASKS="t01 t05"` и `make limit N=5` — подмножества.

## Конфигурация

Задаётся через переменную окружения или соответствующий CLI-флаг.

| Переменная | Дефолт | Назначение |
| --- | --- | --- |
| `BITGN_API_KEY` | — | Нужна для `start_run` (анонимным прогонам тоже). Лежит в `.env`. |
| `BITGN_HOST` / `BENCHMARK_HOST` | `https://api.bitgn.com` | URL харнеса. |
| `BENCHMARK_ID` / `BENCH_ID` | `bitgn/ecom1-dev` | Какой бенчмарк гонять (`…-dev` / `…-prod`). |
| `CONCURRENCY` | `1` | Параллельные trial-воркеры; он же бьёт fan-out `start_trial` и bootstrap. |
| `CLAUDE_MODEL` / `--model` | `claude-sonnet-4-6` | Модель Executor'а. |
| `CLAUDE_REASONING_EFFORT` / `--effort` | `high` | Effort Executor'а (`low`/`medium`/`high`/`xhigh`/`max`). |
| `CLAUDE_MAX_TURNS` | `40` | Жёсткий лимит turn'ов Executor'а. |
| `PA_CLAUDE_MODEL` / `--process-architect-model` | `claude-opus-4-7` | Модель PA. |
| `PA_CLAUDE_REASONING_EFFORT` / `--process-architect-effort` | `xhigh` | Effort PA. |
| `PA_LLM_CONCURRENCY` | `1` | Параллельные сессии PA. `0` — полностью выключить PA (workdir'ы не материализуются, каждый submit → `skipped`). |
| `PA_FIX_ENABLED` / `--pa-fix` | `0` | Включить `failure_fix` + `fix_blind`. |
| `REFRESH_ENABLED` / `--refresh` | `0` | Включить per-unit `refresh`. |
| `WORLD_REFRESH_ENABLED` / `--world-refresh` | `0` | Включить `world_refresh`. |
| `WORLD_CREATE_ENABLED` / `--world-create` | `0` | Использовать `world_create` вместо `world_refresh` для world-PA (пересборка всего BP-набора). |
| `STALE_RESOLUTION` / `--stale-resolution` | `latest_async_refresh` | `latest_async_refresh` — Executor стартует на latest, refresh/world_refresh идут в фоне. `wait_for_refresh` — резолвер ждёт world_refresh; для первого прогона после смены мира. |
| `TRIAL_START_INTERVAL_SEC` | `2` | Минимум секунд между `start_trial` (пауза до вызова, чтобы таймер организатора считал только нашу работу). |
| `BLIND_EMULATION` / `--blind-emulation` | `0` | Эмуляция prod-blind политики на открытом бенчмарке: стек видит `score=null`/пустые hints; реальный вывод грейдера — в соседнем `<run_id>-score/`. |
| `DUMP_SQL_ROWS` / `--dump-sql-rows` | `0` | Если `>0`, дополнительно дампит до N строк на user-таблицу в `dump_sql/`. |
| `RUNS_ROOT` / `--runs-root` | `../../.runs/ecom` | Корень артефактов прогона (относительно корня репо). Задавайте явно для предсказуемости. |
| `SMOKE_TASK` | `t01` | Дефолтный task id для `make smoke`. |

Сабмит: прогоны **по умолчанию сабмитятся**; `--no-submit` оставляет run
открытым (без `submit_run` грейдер не раскрывает score, поэтому `summary.json`
остаётся `score: null` и `failure_fix` не сработает). `--no-process-architect`
гасит только `failure_fix`/`fix_blind`; `--wait-process-architect` блокирует
сабмит на PA. Полный список флагов — `uv run python -m orchestrator.main --help`.

## Чтение результатов

После прогона `<RUNS_ROOT>/<run_id>/` содержит:

- **`report.md`** — человекочитаемый итог: агрегаты в шапке (`wall-clock` /
  `cpu-sum` / `trial-sum` / `boot-sum`) + таблица по задачам (outcome, score,
  refs, тайминги). `trial-sum` — метрика организатора (сумма времени
  `start_trial`→`end_trial`).
- **`summary.json`** — то же машинно.
- **`report_PA.md`** — агрегат PA-jobs (если PA работал).
- **`run.json`** — `run_id`, `harness_run_id`, бенчмарк.

Внутри каждого `NNNN-<task>-<trial>/`:

| Артефакт | Что показывает |
| --- | --- |
| `task.md` | Текст задачи (рандомизируется per-run организатором). |
| `CLAUDE.md`, `business_processes/` | Промпт, который реально увидел Executor (отрендерен резолвером). |
| `vault/`, `bin-help/`, `tree.md` | Дамп живого мира задачи (docs, инструменты, схема БД). |
| `attention/` | Дельта мира vs baseline (drift + relocations), показанная Executor'у. |
| `answer.json`, `result.json` | Финальный ответ (outcome, refs) и итог трайла (score, тайминги, turns, MCP-вызовы). |
| `.logs/transcript.jsonl` | Полный stream-json транскрипт Executor'а. |
| `.logs/mcp-tool-calls.jsonl`, `.logs/python/` | Все вызовы `execute_python` и сниппеты — суть «что делал агент». |
| `.logs/instruction-selection.json` | Какие версии юнитов выбрал резолвер + какой видел world-drift (стабильный «снапшот» прогона). |

Для сравнения двух прогонов сравнивайте **выбор резолвера + world-drift** в
`instruction-selection.json`, а не `task.md` — текст задачи рандомизируется
per-run.

**Примеры прогонов.** В `runs/` лежат заархивированные прогоны `ecom1-dev` для
оффлайн-изучения:

- `20260530-050756` — полный прогон на 53 трайла (точка завершения dev-обучения).
- `20260521-123446` — прогон, где `failure_fix` PA за один проход **дрейфит
  четыре разных процесса**: по четырём проваленным трайлам он починил
  `identity_and_auth`, `discount`, `payments_3ds_recovery` и
  `refs_and_submission`. Загляните в workdir'ы `*-process-architect/pa-output/`,
  чтобы увидеть каждый фикс, его обоснование и выпущенную новую версию юнита.

Распакуйте `tar xzf runs/<id>.tar.gz` и посмотрите артефакты, описанные выше.

## Структура репозитория

```
pyproject.toml / Makefile / uv.lock   # сборка/запуск через uv
orchestrator/                         # детерминированный Python (harness loop, resolver, PA)
instructions/                         # версионированный источник правды
  registry.json                       #   плоский список юнитов
  world.json, world_baseline/vNNNN/   #   foundational «карта мира» + immutable baselines
  units/<id>/vNNNN/                   #   immutable per-unit версии (content + manifest + deps)
  prompts/process_architect/          #   промпты PA (failure_fix / refresh / world_refresh / world_create / conflict)
static-instructions/                  # runtime statics, копируются как есть (runtime_prelude.py, workspace.py, .claude/)
runs/                                 # заархивированные примеры прогонов (tar.gz) — см. «Чтение результатов»
```

<details><summary>Подробная карта кода (orchestrator/)</summary>

```
orchestrator/
  main.py               # CLI + harness loop + проводка прогона
  config.py             # конфиг из env
  harness.py            # хелперы BitGN harness
  bootstrap.py          # PreBootstrapDumper + BinHelpBootstrapper (дамп мира)
  task_dir.py           # материализация per-trial
  claude_runner.py      # спавн `claude -p`, stream-json транскрипт
  mcp_python_server.py  # stdio MCP-сервер с execute_python
  python_executor.py    # раннер сниппетов
  session_registry.py   # opaque session id ↔ harness_url
  report.py             # summary.json + report.md
  sql_schema.py         # генератор bin-help/sqlite_schema.txt
  bp_admin.py           # human-only CLI: retire / rollback / world-baseline
  instructions/
    store.py            #   registry, manifest, обход версий
    fingerprints.py     #   sha256-индекс по vault/ + bin-help/ + static/
    world_baseline.py   #   world-слой (load + drift + запись baseline)
    resolver.py         #   match-or-fallback + рендер task_dir
    versioning.py       #   атомарный writer vNNNN/ + append в registry
    pa_decision.py      #   валидаторы решения + apply
    pa_queue.py         #   приоритетная очередь + per-unit / registry локи
    pa_runner.py        #   спавн PA Claude CLI + post-run артефакты
    pa_workdir.py       #   материализаторы workdir по режимам + ingest
```

</details>

Новые артефакты прогонов пишутся **снаружи** репозитория, под `RUNS_ROOT`;
закоммиченный `runs/` здесь хранит только примеры-архивы.
