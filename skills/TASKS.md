# TASKS.md — Codebase Vitality MVP

Tasks derivadas de `DEPENDENCY_GRAPH.md`. Cada task tem ID, dependências explícitas (por ID de task, não só por feature), critério de pronto, e fase correspondente.

Convenção de ID: `T<fase>.<sequência>`.

---

## Fase 0 — Fundação

### T0.1 — Estrutura inicial do projeto
- **Depende de:** nenhuma
- **Descrição:** criar `pyproject.toml`, layout de pastas conforme `ARCHITECTURE.md` Seção 12 (`src/vitality/`, `tests/`, `docs/`), `LICENSE` (Apache 2.0).
- **Pronto quando:** `pip install -e .` funciona localmente e `vitality --help` roda (mesmo sem subcomandos implementados).

### T0.2 — Schema SQLite (`store/schema.sql`)
- **Depende de:** T0.1
- **Descrição:** criar tabelas `commits`, `declared_dependencies`, `runtime_calls`, `scans` conforme `ARCHITECTURE.md` Seção 5.
- **Pronto quando:** schema aplicado a um `.db` vazio sem erros; cada tabela tem teste de criação.

### T0.3 — Wrapper de store (`store/db.py`)
- **Depende de:** T0.2
- **Descrição:** funções `get_connection()`, `apply_schema()`, helpers de insert/select para cada tabela. Sem ORM (decisão da arquitetura).
- **Pronto quando:** testes unitários cobrem insert + select básico em cada tabela.

---

## Fase 1 — Coletores (paralelizável após Fase 0)

### T1.1 — Comando `vitality init`
- **Depende de:** T0.3
- **Descrição:** cria `.vitality/`, aplica schema, adiciona `.vitality/` ao `.gitignore` automaticamente (Seção 8 do `ARCHITECTURE.md`), falha com mensagem clara se não houver repositório git.
- **Pronto quando:** rodar `vitality init` em repo git real cria a pasta e o `.gitignore` é atualizado; rodar fora de um repo git falha com mensagem clara, não stack trace.

### T1.2 — Coletor de git history (`collector/git_history.py`)
- **Depende de:** T0.3
- **Descrição:** shell out para `git log` com format string explícito (`--pretty=format:...`), parse para registros de commit/arquivo, grava na tabela `commits`.
- **Pronto quando:** rodar contra um repositório de teste (`tests/fixtures/demo_repo`) produz contagem de commits/arquivos correta e verificável manualmente.

### T1.3 — Coletor de runtime trace (`collector/runtime_trace.py`)
- **Depende de:** T0.3
- **Descrição:** usar `coverage.py` para instrumentar execução da suíte de testes do projeto alvo, registrar símbolos chamados em `runtime_calls`.
- **Pronto quando:** rodar contra `demo_repo` com testes conhecidos produz contagens de chamada coerentes com o que os testes de fato exercitam.

### T1.4 — Parser de manifest de dependências
- **Depende de:** T0.1
- **Descrição:** parser para `requirements.txt` (MVP: uma linguagem só, conforme RFC não-objetivo de multi-linguagem), popula `declared_dependencies`. Erros de parsing degradam graciosamente (Seção 9 do `ARCHITECTURE.md`) — não abortam o processo inteiro.
- **Pronto quando:** manifest válido é parseado corretamente; manifest com uma linha malformada ainda produz resultado parcial + warning no stderr.

---

## Fase 2 — Orquestração

### T2.1 — Comando `vitality scan`
- **Depende de:** T1.2, T1.3, T1.4
- **Descrição:** orquestra os três coletores em sequência, cria registro em `scans` com `scan_id` único, marca `finished_at` só se tudo completar sem erro fatal (Seção 9 do `ARCHITECTURE.md`).
- **Pronto quando:** rodar `vitality scan` em `demo_repo` popula todas as tabelas e imprime contagens básicas (commits parseados, símbolos rastreados, duração).

### T2.2 — Tratamento de scan parcial/interrompido
- **Depende de:** T2.1
- **Descrição:** se a suíte de testes do projeto alvo falhar durante o `scan`, persistir dado parcial já coletado, marcar `finished_at = NULL`, sair com código não-zero distinto de "tool quebrou".
- **Pronto quando:** simular falha de teste no meio do scan ainda deixa dado parcial consultável, e reporters avisam que o dado está incompleto.

---

## Fase 3 — Reporters

### T3.1 — `vitality deps` (saída humana)
- **Depende de:** T2.1
- **Descrição:** cruza `declared_dependencies` com `runtime_calls` do scan mais recente, imprime tabela (`used` / `unused`) em formato legível.
- **Pronto quando:** rodar contra `demo_repo` com uma dependência conhecida não usada produz a saída esperada e correta.

### T3.2 — `vitality deps --format json`
- **Depende de:** T3.1
- **Descrição:** mesma lógica de T3.1, saída no shape JSON definido em `ARCHITECTURE.md` Seção 6, incluindo `schema_version`.
- **Pronto quando:** saída valida contra um JSON Schema documentado em `docs/schema.md`; testado com `jq`/parsing automático.

### T3.3 — `vitality query --module <path> --format json`
- **Depende de:** T3.2, T1.2, T1.3
- **Descrição:** generaliza o padrão de saída validado em T3.2 para consulta por módulo — `runtime_calls`, `change_frequency_90d`, `primary_authors`, `has_test_coverage`.
- **Pronto quando:** rodar contra um módulo conhecido de `demo_repo` retorna valores corretos para cada campo; erro claro (JSON estruturado) se o módulo não existir no scan.

### T3.4 — Erro estruturado para "scan ausente"
- **Depende de:** T3.1, T3.3
- **Descrição:** qualquer reporter rodado sem scan prévio retorna mensagem clara (humano) ou JSON de erro estruturado (`{"error": ..., "code": "no_scan_found"}`) — requisito RF8.
- **Pronto quando:** rodar `vitality deps` ou `vitality query` em repo recém-inicializado (sem `scan`) nunca produz stack trace.

---

## Fase 4 — Acabamento

### T4.1 — Documentação de schema (`docs/schema.md`)
- **Depende de:** T0.2, T3.2, T3.3
- **Descrição:** documentar schema SQLite e shape JSON de cada comando, versionado (RNF5).
- **Pronto quando:** documento cobre todas as tabelas e todos os campos JSON expostos, com exemplos reais (não inventados).

### T4.2 — README com exemplo de output real
- **Depende de:** T3.1, T3.2, T3.3
- **Descrição:** README com instalação, exemplo de `vitality scan` + `vitality deps` rodado contra um repositório real (não `demo_repo` sintético) — conforme decisão de produto de validar com case real antes de divulgar.
- **Pronto quando:** alguém de fora consegue seguir o README do zero e reproduzir o mesmo output.

### T4.3 — Benchmark de overhead do runtime trace
- **Depende de:** T1.3
- **Descrição:** medir overhead de `coverage.py` em 2-3 repositórios reais de tamanhos diferentes, validar contra meta de RNF2 (~20%).
- **Pronto quando:** número real documentado; se exceder a meta, abrir task de mitigação (`--sample mode`, já previsto como risco em `ARCHITECTURE.md` Seção 13).

### T4.4 — Empacotamento e publicação no PyPI
- **Depende de:** T4.1, T4.2, T4.3
- **Descrição:** configurar `pyproject.toml` para build, publicar primeira versão (`0.1.0`) no PyPI.
- **Pronto quando:** `pip install codebase-vitality` funciona em uma máquina limpa.

---

## Resumo de ordem (visão linear)

```
T0.1 → T0.2 → T0.3
            ├→ T1.1
            ├→ T1.2 ─┐
            ├→ T1.3 ─┤
            └→ T1.4 ─┘
                      → T2.1 → T2.2
                                → T3.1 → T3.2 → T3.3 → T3.4
                                                          → T4.1 → T4.2 → T4.3 → T4.4
```

**Tasks paralelizáveis hoje, se houver mais de uma pessoa/agente trabalhando:** T1.2, T1.3 e T1.4 podem ser feitas simultaneamente assim que T0.3 estiver pronta.
