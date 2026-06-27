# DEPENDENCY_GRAPH.md — Codebase Vitality MVP

Baseado em `RFC.md` (Seção 10 — MVP) e `ARCHITECTURE.md`. Mapeia cada feature do MVP às suas dependências técnicas, deriva a ordem de implementação correta, e serve de base para `TASKS.md`.

---

## 1. Features do MVP (escopo aprovado)

| ID | Feature | Comando |
|---|---|---|
| F1 | Inicialização do projeto local | `vitality init` |
| F2 | Coleta de histórico git | parte de `vitality scan` |
| F3 | Rastreamento de runtime (instrumentação de testes) | parte de `vitality scan` |
| F4 | Persistência em SQLite | infraestrutura interna |
| F5 | Auditoria de dependências (declaradas vs. usadas) | `vitality deps` |
| F6 | Saída estruturada para consumo por agente | `vitality query --format json` |

`handoff` (F7) e `health` (F8) existem no roadmap, mas estão **fora deste grafo** — só entram quando F1–F6 estiverem validados, conforme já decidido no RFC.

---

## 2. Grafo de dependências

```
F1 (init)
  │
  ▼
F4 (store / schema SQLite)
  │
  ├──────────────┐
  ▼              ▼
F2 (git history) F3 (runtime trace)
  │              │
  └──────┬───────┘
         ▼
   F5 (dependency audit)
         │
         ▼
   F6 (query JSON)
```

**Leitura do grafo:**

- **F1 → F4**: não existe persistência sem que `.vitality/` e o schema existam — `init` é o que cria esse espaço.
- **F4 → F2 e F4 → F3**: tanto o coletor de git history quanto o tracer de runtime escrevem na mesma store; o schema (tabelas `commits`, `runtime_calls`, `scans`) precisa existir antes de qualquer coletor rodar, mesmo que cada coletor seja implementado de forma independente depois.
- **F2 e F3 → F5**: a auditoria de dependências (F5) precisa cruzar dados de **ambos** — uso real (F3) e, indiretamente, contexto de scan (F4/F2 fornecem o `scan_id` usado para correlacionar). F2 e F3 podem ser construídos em paralelo, mas F5 só fica completo quando os dois existem.
- **F5 → F6**: `query` (F6) é uma generalização do formato de saída que `deps` (F5) já precisa resolver primeiro (formatação JSON, `schema_version`, separação dado objetivo vs. experimental). Implementar `deps` primeiro valida o padrão de saída antes de generalizá-lo em `query`.

**Por que F2 e F3 não dependem um do outro:** são fontes de dados independentes (histórico de commits vs. rastreamento de execução). Tratá-los como dependentes um do outro criaria acoplamento artificial — o objetivo da arquitetura (Seção 2 do `ARCHITECTURE.md`) é justamente que cada coletor seja um módulo isolado.

---

## 3. Ordem de implementação

A ordem segue uma travessia topológica do grafo acima, com paralelização explícita onde o grafo permite:

```
Fase 0 — Fundação
  1. Estrutura do projeto (pyproject.toml, layout de pastas)
  2. F4 — Schema SQLite + wrapper de store

Fase 1 — Coletores (paralelizável)
  3. F1 — comando `init`
  4. F2 — coletor de git history
  5. F3 — coletor de runtime trace

Fase 2 — Orquestração
  6. comando `scan` (orquestra F2 + F3, grava na store)

Fase 3 — Reporters
  7. F5 — `deps` (auditoria de dependências)
  8. F6 — `query` (generalização do formato JSON)

Fase 4 — Acabamento
  9. Tratamento de erros (Seção 9 do ARCHITECTURE.md)
  10. README + exemplo real de output
  11. Empacotamento e publicação (PyPI)
```

**Por que o schema (F4) vem antes de qualquer coletor:** os dois coletores escrevem na mesma store; implementá-los antes do schema existir forçaria retrabalho ou um schema implícito não documentado, violando RNF5 (extensibilidade/schema versionado) do `ARCHITECTURE.md`.

**Por que `deps` vem antes de `query`:** `query` é estritamente mais genérico que `deps`. Resolver o formato de saída (JSON, versionamento, separação objetivo/experimental) no caso mais concreto (`deps`) primeiro evita desenhar uma abstração genérica antes de ter um caso real para validá-la — mesmo princípio de "menor produto que gera valor" da skill `product-architect`.

---

## 4. Pontos de paralelização

| Pode ser feito em paralelo | Por quê |
|---|---|
| F2 (git history) e F3 (runtime trace) | Fontes de dados independentes, nenhuma lê o que a outra escreve |
| README/documentação e Fase 3 (reporters) | Documentação não bloqueia código, mas deve referenciar a saída real antes de publicar |

| Não pode ser paralelizado | Por quê |
|---|---|
| F4 antes de F2/F3 | Ambos os coletores dependem do schema existir |
| F2+F3 antes de F5 | `deps` precisa de dado real de ambas as fontes para ser testável de verdade, não só mockado |

---

*Este grafo cobre exclusivamente o MVP (F1–F6). Ao iniciar `handoff` (v0.2) ou `health` (v0.3), este documento deve ser estendido, não reescrito — ambos se conectam a F2/F4 já existentes.*
