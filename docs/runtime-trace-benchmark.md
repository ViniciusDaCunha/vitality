# Runtime Trace Benchmark

Benchmark de overhead do runtime trace baseado em `coverage.py`, conforme RNF2:
`vitality scan` deve adicionar aproximadamente no maximo 20% ao tempo normal da
suite de testes em projetos medios.

## Method

- Data: 2026-06-29
- Python: `python3`
- coverage.py: `7.14.3`
- Repeticoes: 3 por comando
- Numero documentado: mediana do tempo reportado pelo `unittest`
- Ambiente: repositorios locais reais, sem fixtures sinteticas
- Bytecode: `PYTHONDONTWRITEBYTECODE=1`
- Arquivo de coverage: `/tmp/*-benchmark.coverage`

O comando "coverage" usa a mesma suite de testes do baseline, envolvida por
`python3 -m coverage run --data-file <arquivo> -m ...`.

## Results

| Repository | Size | Test command | Baseline | coverage.py | Overhead |
|---|---|---|---:|---:|---:|
| Codebase Vitality | 53 unittest tests | `python3 -m unittest tests.test_cli_deps tests.test_cli_query tests.test_cli_scan tests.test_dependency_manifest tests.test_git_history tests.test_project_structure tests.test_readme tests.test_runtime_trace tests.test_schema tests.test_store_db tests.test_docs_schema` | 3.163s | 3.235s | 2.3% |
| DataVolleyParse / volei_analytics | 29 unittest tests | `python3 -m unittest discover -s tests` | 0.503s | 1.011s | 101.0% |

Raw timings:

| Repository | Baseline runs | coverage.py runs |
|---|---:|---:|
| Codebase Vitality | 3.163s, 3.127s, 3.264s | 3.235s, 3.264s, 3.231s |
| DataVolleyParse / volei_analytics | 0.503s, 0.464s, 0.503s | 1.011s, 1.035s, 0.901s |

## RNF2 Decision

RNF2 target: approximately 20% overhead.

- Codebase Vitality: 2.3%, within target.
- DataVolleyParse / volei_analytics: 101.0%, outside target.

The DataVolleyParse result is a small and very fast suite, so fixed startup and
coverage initialization costs dominate the percentage. Still, it exceeds RNF2
and must be treated as a launch risk for small repositories.

## Mitigation

Mitigation task opened in `TASKS.md`: add an opt-in `--sample mode` for runtime
trace so small or latency-sensitive repositories can trace a subset of test
execution when full `coverage.py` overhead is too high.
