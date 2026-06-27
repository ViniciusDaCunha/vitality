# ARCHITECTURE.md — Codebase Vitality

**Escopo coberto:** MVP conforme definido na Seção 10 do `RFC.md` — `init`, `scan`, `deps`, `query --format json`, somente local, sem servidor, sem telemetria.
**Status:** Rascunho, alinhado com o RFC aprovado.

---

## 1. Visão Geral do Sistema

Codebase Vitality é uma **ferramenta de CLI local-first** que responde a uma pergunta com dados reais em vez de suposições: *"essa dependência/função é realmente usada?"* Ela faz isso combinando duas fontes de dados baratas e simples — o histórico do `git log` e rastreamento (tracing) leve em tempo de execução durante os testes — em um único banco de dados SQLite local, e então expõe esses dados através de uma CLI e de um modo de saída em JSON pensado para ser consumido por agentes de codificação de IA.

Não há servidor, não há separação cliente-servidor, nenhuma chamada de rede exceto a instalação do próprio pacote. O sistema todo roda como um único processo invocado pelo terminal, com escopo de um repositório por vez.

```
┌─────────────────────────────────────────────┐
│              vitality (CLI)                  │
│                                                │
│  init → scan → deps / query                   │
│                                                │
│  ┌─────────────┐      ┌────────────────────┐ │
│  │  Collector   │ ──→  │  .vitality/data.db  │ │
│  │ (git + trace)│      │     (SQLite)        │ │
│  └─────────────┘      └────────────────────┘ │
│                              │                 │
│                              ▼                 │
│                     ┌────────────────┐         │
│                     │   Reporters    │         │
│                     │ (deps, query)  │         │
│                     └────────────────┘         │
└─────────────────────────────────────────────┘
```

**Por que esse formato:** os próprios requisitos não funcionais do RFC (RNF1 privacidade, RNF4 portabilidade) já descartam um servidor desde o início. Um único processo local com um arquivo local como único estado é a coisa mais simples que pode funcionar, e também é a mais fácil de auditar por terceiros (ou por um agente de IA) — não há backend oculto para confiar.

---

## 2. Módulos Principais

| Módulo | Responsabilidade |
|---|---|
| `cli` | Parsing de argumentos, despacho de comandos, formatação de saída legível para humanos |
| `collector.git_history` | Faz o parsing do `git log` em registros estruturados de commits/alterações de arquivos |
| `collector.runtime_trace` | Conecta-se à execução dos testes para registrar quais imports/funções realmente foram executados |
| `store` | Camada fina sobre o SQLite — definição de schema, migrações, leitura/escrita |
| `reports.dependency_audit` | Cruza dependências declaradas (manifesto) com os dados de rastreamento em tempo de execução |
| `reports.query` | Exportação genérica de dados estruturados (JSON), o contrato voltado para agentes |

**Por que uma estrutura plana de módulo-por-responsabilidade em vez de um framework:** o sistema é pequeno o suficiente (processo único, escopo de repositório único) para que introduzir uma arquitetura de plugins ou um framework de injeção de dependência seria resolver um problema que ainda não existe. Cada módulo é um pacote Python simples com uma única responsabilidade clara; essa é a escolha "sem graça" e também a mais fácil de estender depois (Seção 13 — itens do Roadmap como `handoff`/`health` simplesmente adicionam novos módulos sob `reports/`).

---

## 3. Responsabilidades do Frontend

Não há frontend no sentido tradicional — a saída do terminal da CLI **é** a UI. Suas responsabilidades:

- Renderizar tabelas legíveis para humanos em `vitality deps` (dependências declaradas vs. usadas)
- Renderizar JSON para `vitality query --format json`, com nomes de campos estáveis e documentados (esse é o "frontend" de fato para consumidores agentes)
- Distinção clara na saída entre **dados objetivos** (auditoria de deps) e qualquer coisa marcada como `--experimental` (conforme RNF6), para que nem um humano nem um agente confiem demais em sinais não validados
- Códigos de saída significativos para scripting/CI (`0` = limpo, diferente de zero = encontrou deps não usadas), de modo que a ferramenta se componha com pipelines de shell e CI sem precisar de um "frontend" de verdade

**Por que nenhuma UI web no MVP:** um dashboard é uma tentação forte, mas adiciona toda uma superfície de implantação (hospedagem, autenticação, pipeline de build) para uma ferramenta cuja prova de valor principal no RFC é um único número ("X% das dependências nunca são usadas"). Uma tabela no terminal prova esse número igualmente bem. A UI web é um ponto de extensão, não um requisito (Seção 13).

---

## 4. Responsabilidades do Backend

"Backend" aqui significa o collector + store, já que não há serviço voltado para rede.

- **`collector.git_history`**: executa o `git log` via shell com uma string de formato fixa e parseável; faz o parsing em registros de commit (autor, data, arquivos tocados). Não usa GitPython ou bibliotecas wrapper semelhantes — o próprio `git` já está instalado em todos os lugares onde essa ferramenta vai rodar, e chamá-lo via shell é mais simples e mais portátil do que adicionar uma biblioteca de binding com sua própria superfície de compatibilidade de versões.
- **`collector.runtime_trace`**: usa o hook nativo do Python `sys.settrace`/no estilo `coverage.py` (reaproveitar o `coverage.py` é preferível a um tracer feito à mão — é uma dependência madura e amplamente confiável que já resolve as partes difíceis do rastreamento de chamadas).
- **`store`**: SQLite via o módulo nativo `sqlite3` do Python. Sem ORM. O schema é pequeno e estável o suficiente para que SQL puro com uma camada auxiliar fina seja mais fácil de entender — e também mais fácil para um agente externo consultar diretamente, se quiser contornar a CLI (RNF5, extensibilidade).

**Por que SQLite em vez de Postgres/outra coisa:** zero instalação, zero processo para gerenciar, um único arquivo que fica em `.vitality/` e pode ser ignorado pelo `.gitignore` ou commitado se uma equipe quiser compartilhar os resultados de scan. Isso atende diretamente à RNF4 (portabilidade) e à RNF1 (privacidade — nada sai da máquina por construção, não há servidor de banco de dados para configurar errado).

---

## 5. Modelo de Dados

Três tabelas cobrem todo o escopo do MVP:

```sql
-- Uma linha por alteração de arquivo em um commit
CREATE TABLE commits (
    commit_hash   TEXT NOT NULL,
    author        TEXT NOT NULL,
    committed_at  TEXT NOT NULL,   -- ISO 8601
    file_path     TEXT NOT NULL,
    PRIMARY KEY (commit_hash, file_path)
);

-- Uma linha por dependência declarada (extraída do manifesto)
CREATE TABLE declared_dependencies (
    name          TEXT PRIMARY KEY,
    version_spec  TEXT,
    source_file   TEXT NOT NULL    -- ex.: requirements.txt, package.json
);

-- Uma linha por (dependência ou função) chamada observada em tempo de execução
CREATE TABLE runtime_calls (
    symbol        TEXT NOT NULL,   -- nome do módulo ou nome de função qualificado
    call_count    INTEGER NOT NULL DEFAULT 0,
    last_scan_id  TEXT NOT NULL,
    PRIMARY KEY (symbol, last_scan_id)
);

CREATE TABLE scans (
    scan_id    TEXT PRIMARY KEY,   -- uuid
    started_at TEXT NOT NULL,
    finished_at TEXT
);
```

**Por que um schema minimalista como esse:** o escopo do MVP no RFC é exatamente `deps` + `query`. A tabela `commits` existe agora (é barata de coletar) porque será necessária para o `handoff` na v0.2, e coletá-la depois significaria re-escanear todo o histórico — mas ela **não é exposta** por nenhum comando do MVP ainda. Essa é a regra de "deixar pontos de extensão limpos" aplicada concretamente: coletar o que é barato e estável agora, expor apenas o que está validado agora.

**Por que não um schema genérico de chave-valor/event-log:** seria mais "à prova de futuro" no papel, mas mais difícil de consultar diretamente com SQL hoje, e o não-objetivo explícito do RFC é evitar generalidade especulativa antes que o MVP prove seu valor.

---

## 6. Contratos de API

Não há API de rede. O "contrato" é a saída em JSON da CLI, já que é isso que a RF6 exige para consumo por agentes.

### `vitality deps --format json`

```json
{
  "scan_id": "uuid",
  "generated_at": "2026-06-24T12:00:00Z",
  "dependencies": [
    {
      "name": "lodash",
      "declared": true,
      "runtime_calls": 0,
      "status": "unused"
    },
    {
      "name": "requests",
      "declared": true,
      "runtime_calls": 482,
      "status": "used"
    }
  ]
}
```

### `vitality query --module <path> --format json`

```json
{
  "module": "src/payments/webhook.py",
  "runtime_calls": 12,
  "change_frequency_90d": 34,
  "primary_authors": ["maria"],
  "has_test_coverage": false
}
```

**Por que um formato de JSON simples e explícito em vez de algo como GraphQL ou uma linguagem de consulta genérica:** os consumidores são scripts de CLI e agentes de IA lendo a saída padrão (stdout), não clientes de navegador fazendo consultas ad-hoc. Um formato JSON fixo e versionado por comando é mais simples de documentar, mais simples de escrever um JSON Schema depois, e evita construir uma infraestrutura de API real para uma ferramenta que não tem servidor para hospedá-la.

**Versionamento:** toda saída JSON inclui um campo de nível superior `schema_version` (omitido acima por brevidade) começando em `"1.0"`, para que agentes e scripts possam detectar mudanças que quebram compatibilidade sem precisar adivinhar.

---

## 7. Integrações Externas

O MVP tem exatamente uma superfície de dependência externa: **a própria instalação de `git` do usuário** e **o test runner já em uso no repositório de destino** (pytest, etc., invocado como subprocesso para alimentar o rastreador em tempo de execução).

Nenhum serviço externo, nenhuma chave de API, nenhuma dependência de SaaS, nenhum endpoint de telemetria — isso é consequência direta da RNF1 (privacidade) e do não-objetivo de descartar um serviço centralizado na v1.

**Por que não integrar com APIs do GitHub/GitLab no MVP:** isso adicionaria gerenciamento de autenticação/token sem nenhum benefício para o escopo do MVP (`deps` e `query` não precisam desses dados). Isso só se torna relevante para a ideia de "abrir uma issue" do `handoff`, explicitamente postergada no roadmap do RFC (v0.2+), e mesmo assim deveria ser opt-in, não padrão.

---

## 8. Modelo de Autenticação/Segurança

Não há autenticação, porque não há superfície multiusuário ou fronteira de rede no MVP — é uma ferramenta de CLI de usuário único, operando em arquivos locais com as permissões de quem a executa.

Considerações de segurança que se aplicam:
- **Nenhum dado sai da máquina** por construção (nenhuma chamada de rede no collector ou nos reporters) — esse é o modelo de segurança real, não controle de acesso.
- **O rastreamento em tempo de execução executa a própria suíte de testes do projeto** — isso significa que `vitality scan` executa código arbitrário do repositório de destino, com a mesma fronteira de confiança que rodar `pytest` diretamente. Nenhum sandboxing adicional é adicionado no MVP; isso deve ser documentado claramente no README para que os usuários entendam que `scan` é exatamente tão confiável quanto rodar seus próprios testes.
- O **arquivo SQLite em `.vitality/`** deve ser adicionado ao `.gitignore` por padrão via `vitality init`, já que pode conter nomes de autores e caminhos de arquivos que uma equipe pode não querer commitar por padrão (compartilhamento opt-in, não padrão).

**Por que nenhum sandboxing na v1:** construir um sandbox seguro para execução arbitrária de testes é um investimento de engenharia significativo que não corresponde ao escopo do MVP, e a fronteira de confiança é idêntica à que já existe quando um desenvolvedor roda sua própria suíte de testes localmente. Sinalizado aqui explicitamente como uma limitação conhecida, não uma lacuna silenciosa.

---

## 9. Tratamento de Erros

- **Repositório git ausente**: `vitality init`/`scan` falham rapidamente com uma mensagem clara ("not a git repository") em vez de produzir silenciosamente um banco de dados vazio.
- **Falha parcial de scan** (ex.: a própria suíte de testes falha): o collector ainda persiste os dados de rastreamento coletados antes da falha, e o `scan` retorna código de saída diferente de zero, separando claramente "a ferramenta falhou" de "seus testes falharam." Um scan é marcado com `finished_at = NULL` na tabela `scans` se for interrompido, para que os reporters possam avisar o usuário de que os dados estão incompletos.
- **Dados ausentes ao executar um reporter** (ex.: `vitality deps` antes de qualquer `scan` ter sido executado): erro claro e acionável — não um stack trace — informando ao usuário para rodar `vitality scan` primeiro (isso é explicitamente mencionado na RF8).
- **Erros de parsing do manifesto** (`requirements.txt`/`package.json` malformados): degradar graciosamente — pular a entrada não-parseável, avisar via stderr, continuar com o restante, em vez de abortar toda a auditoria por causa de uma linha ruim.

**Por que isso importa especificamente para uma ferramenta voltada a agentes:** um agente de IA chamando `vitality query` programaticamente precisa distinguir "sem dados" de "ferramenta quebrada" de "seu código quebrou" através de códigos de saída e JSON de erro estruturado (`{"error": "...", "code": "..."}` em stderr/saída JSON), não exceções em texto livre — esse é um requisito direto para ser embutido com segurança no loop de decisão de um agente.

---

## 10. Observabilidade

Nenhuma stack de observabilidade externa (sem Sentry, sem Datadog) — contradiria a RNF1 e o não-objetivo explícito de não ser uma ferramenta de APM.

O que o MVP inclui:
- `vitality scan` imprime duração e contagens básicas (commits analisados, símbolos rastreados) na saída padrão, para que os usuários possam verificar que a ferramenta realmente fez algo.
- Uma flag `--verbose` ativa logging em nível de debug para o stderr (módulo `logging` padrão do Python — sem framework de logging personalizado).
- Todo scan é registrado com timestamp e recebe um `scan_id`, para que comparações históricas (usadas depois pelo `health --compare` no roadmap) sejam possíveis sem reestruturar o schema.

**Por que isso é suficiente por agora:** o público é um único desenvolvedor rodando uma CLI localmente, não uma equipe de plantão monitorando um serviço em produção. O investimento em observabilidade deve escalar com a complexidade operacional, e o MVP não tem nenhuma.

---

## 11. Modelo de Implantação

Não há implantação no sentido tradicional — distribuição, não implantação, é o conceito relevante.

- **Canal de distribuição:** PyPI (`pip install codebase-vitality`), conforme discutido anteriormente.
- **Ambiente de execução:** máquina local do desenvolvedor ou executor de CI, Python 3.10+, nenhum container necessário para uso normal.
- **Integração com CI (opcional, não exigido no MVP):** `vitality scan && vitality deps` pode ser adicionado como uma etapa de CI; a falha por limites de dependências não usadas é opt-in via código de saída, não forçada.

**Por que nenhum requisito de Docker/container no MVP:** toda a proposta de valor da ferramenta (RNF4) é "funciona com zero infraestrutura." Exigir Docker para executar uma CLI que já roda em qualquer lugar onde Python e git rodem contradiria diretamente isso. A containerização é irrelevante até/a menos que um componente de servidor seja introduzido (atualmente não está planejado — ver não-objetivos do RFC).

---

## 12. Estrutura de Pastas

```
codebase-vitality/
├── pyproject.toml
├── README.md
├── LICENSE                      # Apache 2.0
├── src/
│   └── vitality/
│       ├── __init__.py
│       ├── cli.py                # parsing de argumentos + despacho de comandos
│       ├── collector/
│       │   ├── __init__.py
│       │   ├── git_history.py
│       │   └── runtime_trace.py
│       ├── store/
│       │   ├── __init__.py
│       │   ├── schema.sql
│       │   └── db.py             # camada fina sobre sqlite3
│       └── reports/
│           ├── __init__.py
│           ├── dependency_audit.py
│           └── query.py
├── tests/
│   ├── test_git_history.py
│   ├── test_runtime_trace.py
│   ├── test_dependency_audit.py
│   └── fixtures/
│       └── demo_repo/            # repositório git minúsculo usado em testes de integração
└── docs/
    └── schema.md                 # schema de DB/JSON documentado e versionado (RNF5)
```

**Por que essa estrutura:** `collector/`, `store/`, `reports/` mapeiam 1:1 para a tabela de módulos da Seção 2 — não há indireção entre "onde uma responsabilidade vive conceitualmente" e "onde seu código vive no disco." `reports/handoff.py` e `reports/health.py` (v0.2/v0.3 no roadmap) se encaixam no pacote `reports/` existente sem reestruturar nada — esse é o ponto de extensão concreto solicitado pelo briefing.

---

## 13. Riscos Técnicos

| Risco | Por que importa | Mitigação nesta arquitetura |
|---|---|---|
| **O rastreamento em tempo de execução só vê os caminhos de código exercitados pelos testes** (já sinalizado como um trade-off no RFC) | Uma dependência/função genuinamente usada apenas em produção, mas não cobertas por testes, será incorretamente marcada como "não usada" | A saída de `deps` reporta explicitamente o contexto de cobertura de testes junto com o status de uso, e o README deve declarar essa limitação com destaque — nunca apresentada silenciosamente como verdade absoluta |
| **`coverage.py` como dependência de rastreamento adiciona overhead** | Pode exceder a meta da RNF2 (~20% de overhead) em suítes de teste grandes | Fazer benchmark contra alguns tamanhos reais de repositório antes do lançamento da v0.1; permitir um modo `--sample` (rastrear um subconjunto das execuções de teste) como alternativa se o overhead for muito alto |
| **Bloqueio de schema uma vez que agentes comecem a depender do formato JSON do `query` (RF6)** | Quebrar o contrato JSON quebra toda integração de agente construída sobre ele | Campo `schema_version` desde o primeiro dia (Seção 6); tratar qualquer remoção/renomeação de campo como um aumento de versão major, adições como minor |
| **O parsing do `git log` é frágil entre versões/locales do git** | Versões diferentes do git ou configurações de locale não-inglês podem mudar sutilmente a formatação da saída do `git log` | Usar uma string de formato explícita e legível por máquina (`--pretty=format:...`) em vez de fazer parsing da saída padrão legível para humanos, e fixar/testar contra uma versão mínima documentada do git |
| **Arquivo SQLite commitado acidentalmente, expondo dados de autor/arquivo em um repositório público** | Expectativa de privacidade (RNF1) violada por padrão se a entrada do `.gitignore` não for adicionada corretamente | `vitality init` escreve a entrada do `.gitignore` automaticamente e avisa se `.vitality/` já estiver sendo rastreado pelo git |
| **Scope creep em direção a `handoff`/`health` antes que `deps` seja validado** | O RFC enquadra explicitamente `deps` como a funcionalidade de menor risco e maior confiança, destinada a provar primeiro a tese central da ferramenta | Esta arquitetura intencionalmente mantém a coleta de `commits` barata mas não exposta (Seção 5), de modo que funcionalidades futuras sejam aditivas, não uma reescrita — mas é a disciplina da equipe, não a arquitetura por si só, que evita o scope creep |

---

*Esta arquitetura deve ser revisitada depois que `vitality scan` + `deps` tiverem rodado contra um repositório real e não trivial, e produzido os primeiros números concretos referenciados na discussão de "case" do RFC — taxas reais de overhead e falsos positivos podem exigir ajustes nos limiares da Seção 9 ou nas mitigações da Seção 13.*
