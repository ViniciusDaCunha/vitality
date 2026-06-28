# RFC: Codebase Vitality

**Status:** Draft
**Autor:** —
**Data:** Junho 2026

---

## 1. Problema

Agentes de IA (Claude Code e similares) hoje refatoram e dão manutenção em código baseando-se quase exclusivamente em **contexto estático**: o conteúdo dos arquivos, grafo de imports, e o que está documentado. Isso gera três classes recorrentes de falha:

1. **Blast radius incorreto** — o agente não sabe se uma função é chamada milhares de vezes em produção ou se é código morto, porque "é importada em algum lugar" não significa "é executada de fato".
2. **Falta de noção de fragilidade** — o agente trata um módulo estável há anos e um módulo reescrito 30 vezes no último mês com o mesmo nível de cautela, porque não tem acesso ao histórico real de mudanças.
3. **Regressões silenciosas** — testes verdes (ou ausência de testes) não capturam mudanças sutis de comportamento; o agente não tem como validar se uma refatoração alterou comportamento de forma inesperada além do que os testes cobrem.

O resultado: refatorações feitas por agentes carregam um risco difícil de quantificar, o que limita a confiança de equipes em delegar manutenção real (não só geração de código novo) para IA.

---

## 2. Objetivos

- Coletar dados objetivos sobre o **uso real em runtime** de dependências e funções (não apenas uso declarado/estático).
- Coletar e estruturar o **histórico de git** como sinal de fragilidade (frequência de mudança, autoria, cobertura de testes por área).
- Gerar um **score de comportamento sob mutação leve** como sinal complementar a testes tradicionais.
- Expor esses três sinais via **CLI para humanos** e via **API/schema consumível por agentes de IA**, para que refatorações sejam informadas por contexto real, não apenas estático.
- Tornar o projeto open source, com a primeira feature (auditoria de dependências) validável e útil de forma isolada, sem depender das demais.

## 3. Não objetivos

- **Não** é um agente de refatoração em si — é uma camada de contexto que outros agentes (Claude Code, etc.) consomem.
- **Não** executa nenhuma ação destrutiva ou automática no código (remover dependência, deletar função, abrir PR) na v1 — tudo é relatório/sinal, decisão fica com humano ou agente downstream.
- **Não** substitui suíte de testes, cobertura de testes ou CI existente — complementa, não substitui.
- **Não** pretende ser uma ferramenta de observability/APM completa (Datadog, Sentry) — o runtime tracing é local e leve, focado em uso de dependências/funções, não em performance ou erros de produção.
- **Não** cobre, na v1, linguagens além do ecossistema inicial (Python e/ou JS/TS) — multi-linguagem é roadmap futuro, não escopo do MVP.

## 4. Usuários

| Usuário | Necessidade |
|---|---|
| **Dev individual / mantenedor de OSS** | Saber o que pode remover/limpar com segurança; gerar handoff antes de sair de um projeto |
| **Equipe de engenharia em empresa** | Reduzir risco de regressão ao usar agentes de IA para manutenção de código legado |
| **Agente de IA (Claude Code e similares)** | Consumir dados de uso real e fragilidade antes de propor/executar refatorações |
| **Tech lead / arquiteto** | Visão de quais áreas do sistema são frágeis e merecem atenção antes de delegar trabalho a agentes |

## 5. Fluxos

### Fluxo 1 — Setup e coleta (humano)
1. `vitality init` no repositório
2. `vitality scan` → roda instrumentação de runtime (durante execução de testes/app) + parse de `git log`
3. Dados populam SQLite local em `.vitality/`

### Fluxo 2 — Consulta humana
1. `vitality deps` → lista dependências declaradas vs. usadas
2. `vitality handoff` → gera `handoff.md`
3. `vitality health` (experimental) → score de variação sob mutação

### Fluxo 3 — Consumo por agente de IA
1. Antes de refatorar um módulo, agente consulta a API/schema local do Vitality (`vitality query --module X --format json`)
2. Agente recebe: uso real de funções no módulo, score de fragilidade histórica, cobertura de testes associada
3. Agente ajusta estratégia: refatoração direta (baixo risco) vs. proposta + confirmação humana (alto risco)
4. Pós-refatoração, agente roda `vitality health --compare` para validar se o comportamento sob mutação degradou

### Fluxo 4 — Handoff de projeto
1. Mantenedor saindo de um projeto roda `vitality handoff`
2. Documento gerado é revisado e ajustado manualmente
3. Documento serve de contexto tanto para humano sucessor quanto para agente de IA em manutenções futuras

## 6. Requisitos funcionais

- **RF1**: Coletar histórico de commits (autor, data, arquivo, frequência de mudança por arquivo/módulo).
- **RF2**: Instrumentar execução (testes e/ou app) para registrar quais imports/funções são de fato chamados em runtime.
- **RF3**: Cruzar dependências declaradas (manifest do projeto) com uso real detectado, produzindo lista de "nunca usadas".
- **RF4**: Gerar documento de handoff em Markdown a partir do histórico de commits (autores principais, áreas frágeis, decisões inferidas).
- **RF5**: Rodar mutações leves no código e medir variação de comportamento (resultado de testes) antes/depois, produzindo score por módulo.
- **RF6**: Expor todos os dados coletados via comando que retorna JSON estruturado, consumível programaticamente.
- **RF7**: Persistir todos os dados localmente (SQLite), sem dependência de serviço externo ou envio de dados.
- **RF8**: CLI com comandos independentes (`scan`, `deps`, `handoff`, `health`, `query`) — cada um deve funcionar mesmo se os outros nunca foram executados (com aviso de dado ausente).

## 7. Requisitos não funcionais

- **RNF1 — Privacidade**: nenhum dado do repositório sai da máquina local por padrão; zero telemetria sem opt-in explícito.
- **RNF2 — Performance**: `vitality scan` não deve adicionar mais que ~20% de overhead ao tempo normal de execução da suíte de testes em projetos médios.
- **RNF3 — Não destrutivo**: nenhum comando da v1 modifica, deleta ou commita código automaticamente.
- **RNF4 — Portabilidade**: deve funcionar sem servidor, sem infraestrutura externa — só Python/CLI local.
- **RNF5 — Extensibilidade**: schema do banco deve ser documentado e versionado, permitindo que outras ferramentas (incluindo agentes de IA) leiam diretamente, não só via CLI.
- **RNF6 — Transparência**: qualquer score "experimental" (ex: `health`) deve ser sinalizado claramente como tal na saída, distinto de dados objetivos (ex: `deps`).
- **RNF7 — Licença**: Apache 2.0, para facilitar adoção corporativa.

## 8. Trade-offs

| Decisão | Ganho | Custo |
|---|---|---|
| Instrumentação via testes existentes, não via produção real | Simplicidade, zero infra | Código não exercitado pelos testes fica invisível (falso "não usado") |
| SQLite local em vez de serviço centralizado | Privacidade, zero setup | Sem visão agregada entre múltiplos repositórios/times sem trabalho manual |
| Nenhuma ação automática no código | Reduz risco de quebra/decisão indevida | Exige sempre um humano ou agente downstream para agir — ferramenta nunca "resolve" sozinha |
| Mutação leve como sinal de saúde | Sinal mais rico que testes verdes/vermelhos | Métrica nova, sem benchmark de mercado — comunidade pode não confiar de imediato |
| Foco em 1-2 linguagens no MVP | Qualidade e foco de engenharia | Limita adoção inicial fora desses ecossistemas |

## 9. Alternativas descartadas

- **Análise puramente estática (tipo `depcheck`/`ts-prune`)**: descartada como abordagem única porque gera falsos positivos/negativos em imports dinâmicos e condicionais — é complementar, não substituta, do runtime tracing.
- **Decaimento automático de conexões não usadas** (remover dependência automaticamente): descartado por risco — falso positivo pode quebrar caminho raramente exercitado (ex: tratamento de exceção, rotina sazonal).
- **Geração automática de issue "procura-se mantenedor"** sem revisão humana: descartado por risco social/reputacional — pode ser invasivo ou constrangedor para o autor original.
- **Serviço centralizado/SaaS** em vez de ferramenta local: descartado na v1 por contradizer o objetivo de privacidade e simplicidade de adoção; pode ser revisitado como opção futura, nunca como padrão.
- **Cobrir múltiplas linguagens desde o início**: descartado para não diluir qualidade do MVP; melhor provar a tese em um ecossistema antes de generalizar.

## 10. MVP

Escopo mínimo, construível e validável em poucos dias:

- `vitality init` + `vitality scan` (git history + runtime tracing básico via hook em testes)
- `vitality deps` — auditoria de dependências declaradas vs. usadas (feature mais objetiva e de menor risco)
- `vitality query --format json` — saída estruturada mínima, já pensando em consumo por agente
- Documentação inicial (README com exemplo de output real em um repositório de demonstração)
- Licença Apache 2.0 publicada desde o primeiro commit

`handoff` e `health` ficam fora do MVP estrito — entram na primeira iteração pós-lançamento, já sinalizados como `--experimental` quando chegarem.

## 11. Roadmap

**v0.1 (MVP)**
- `scan` + `deps` + `query` (JSON)
- Repositório aberto, README com case real

**v0.2**
- `handoff` (geração de documento de handoff a partir do git log)
- Primeiros testes de integração com um agente de IA consumindo `query` antes de refatorar

**v0.3**
- `health` (score de mutação leve), marcado como experimental
- Caso de uso documentado: comparação de regressões em refatoração feita com vs. sem contexto Vitality

**v0.4+**
- Suporte a uma segunda linguagem do ecossistema (ex: JS/TS além de Python, ou vice-versa)
- Integração nativa com CI (rodar `scan` automaticamente em pipeline)
- Possível modo opcional de agregação entre repositórios para times (sempre opt-in, nunca padrão)

---

*Este RFC é um documento vivo — decisões aqui podem mudar conforme o MVP gerar dados reais que confirmem ou refutem as hipóteses do projeto.*
