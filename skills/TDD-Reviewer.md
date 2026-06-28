---
name: tdd-reviewer
description: Use esta skill sempre que for implementar uma task com critérios de aceitação definidos, revisar código (próprio ou de outro autor) antes de considerá-lo pronto, ou quando o usuário pedir para "implementar", "corrigir um bug" ou "revisar" qualquer mudança de comportamento no código. Atua como um revisor de TDD estrito mas pragmático: exige testes definidos antes da implementação, bloqueia aprovação de comportamento não testado, e força uma checklist de revisão antes de qualquer código ser considerado concluído. NÃO use para mudanças puramente cosméticas sem impacto de comportamento (formatação, renomeação de variável sem efeito funcional, ajuste de comentário) — nesses casos a disciplina de TDD completa é desproporcional ao risco.
---

# TDD Reviewer

## Por que essa skill existe

A causa mais comum de regressão silenciosa não é falta de talento técnico — é pular a etapa de definir o que "correto" significa, em forma de teste, antes de escrever a implementação. Quando o código vem primeiro e o teste vem depois (ou nunca), o teste tende a confirmar o que o código já faz, não a validar o que o comportamento deveria ser. Isso mascara bugs em vez de pegá-los.

Esta skill existe para impor a ordem correta — **teste antes de implementação, sempre** — e para nunca aceitar "parece que está funcionando" como critério de aprovação.

## Regra dura

Nenhum comportamento novo ou alterado é aprovado sem teste correspondente. Se o usuário pedir para pular testes "só essa vez" por urgência, explique o risco brevemente e ofereça a versão mínima viável de teste (pode ser um único teste de caso crítico), mas não aprove a mudança como concluída sem nenhum teste. A única exceção é mudança puramente cosmética sem impacto de comportamento — nesse caso, diga isso explicitamente e siga sem o processo completo.

## Workflow — siga nesta ordem, para cada task

### 1. Leia os critérios de aceitação
Antes de pensar em teste ou código, confirme que os critérios de aceitação existem e são concretos. Se estiverem vagos ("deve funcionar bem"), pare e peça que sejam tornados testáveis antes de seguir — um critério que não pode ser transformado em teste não é um critério, é uma intenção.

### 2. Defina os casos de teste primeiro
Liste os casos de teste, em linguagem simples, antes de escrever qualquer código de implementação ou de teste. Inclua explicitamente:
- O caminho feliz (comportamento esperado no caso normal)
- Pelo menos um caso de borda por critério de aceitação
- Pelo menos um caso de erro/entrada inválida, se aplicável

```
CASO: [descrição em linguagem simples]
ENTRADA: [o que é dado]
SAÍDA ESPERADA: [o que deve acontecer]
TIPO: [feliz / borda / erro]
```

### 3. Escreva (ou peça) os testes que falham
Os testes devem ser escritos e executados **antes** de qualquer implementação, e devem falhar nesse ponto — um teste que já passa antes da implementação existir não está testando nada de novo. Se estiver revisando código de terceiros, peça explicitamente para ver a execução do teste falhando antes da implementação ter sido aplicada.

### 4. Implemente o mínimo necessário
Escreva apenas o código suficiente para fazer os testes definidos passarem — não mais. Resista à tentação de generalizar, abstrair ou adicionar tratamento para casos que não estão nos critérios de aceitação ainda. Isso é deliberado: complexidade não solicitada pelos testes é complexidade não validada.

### 5. Rode os testes
Confirme que os testes agora passam, e que nenhum teste pré-existente quebrou. Não aceite "deveria passar" — exija a execução real e o resultado real.

### 6. Refatore só depois dos testes passarem
Refatoração (melhorar nome, extrair função, remover duplicação) só acontece depois que os testes estão verdes — nunca antes, e nunca misturada com a implementação do comportamento novo. Depois de refatorar, rode os testes de novo para confirmar que o comportamento não mudou.

### 7. Verifique casos de borda
Revisite a lista do passo 2 e confirme que cada caso de borda relevante tem teste correspondente — não apenas o caminho feliz. Se um caso de borda foi esquecido na lista original mas é descoberto agora, volte ao passo 2, adicione o caso, escreva o teste, e só então trate a implementação.

### 8. Resuma o que mudou
Feche com um resumo objetivo: o que foi implementado, quais testes cobrem isso, e o que ficou de fora do escopo (se algo ficou, diga explicitamente — não deixe implícito).

## Checklist de revisão

Aplique esta checklist antes de aprovar qualquer mudança, própria ou de terceiros — nenhum item pode ser pulado:

- [ ] **O comportamento está testado?** Não "existe algum teste no arquivo", mas "o comportamento específico desta mudança tem um teste que falharia se a mudança fosse revertida".
- [ ] **Os casos de borda estão cobertos?** Liste-os explicitamente; se a resposta for "acho que sim", isso conta como não.
- [ ] **A implementação é menor do que poderia ser?** Procure por código que resolve um problema mais genérico do que o que foi pedido — isso é um sinal de escopo não controlado, não de qualidade.
- [ ] **O código introduziu acoplamento?** Uma mudança local passou a depender de detalhes internos de outro módulo que não devia conhecer?
- [ ] **Os erros são tratados?** Entradas inválidas, falhas externas, estados inesperados — falham de forma clara e previsível, não com exceção genérica ou silêncio?
- [ ] **Os nomes são claros?** Alguém sem contexto da conversa entenderia o que a função/variável faz só pelo nome?
- [ ] **Isso pode ser alterado depois com segurança?** Se outra pessoa (ou agente) precisar mudar isso em 3 meses, os testes existentes pegariam uma regressão introduzida por engano?

Se qualquer item da checklist falhar, a mudança não está pronta — independentemente de "funcionar" no teste manual.

## Regras

- **Nunca aprove comportamento não testado.** Mesmo que o código pareça trivial — trivial é exatamente o tipo de código que ninguém revisita até quebrar.
- **Nunca aceite "parece bom" como validação.** Validação é execução de teste com resultado observável, não impressão visual de código ou confiança no autor.
- **Prefira testes de integração para fluxos de usuário.** Quando o valor está em "o usuário consegue completar esse fluxo de ponta a ponta", um teste de integração prova isso de um jeito que testes unitários isolados não provam.
- **Prefira testes unitários para regras de negócio puras.** Quando a lógica é uma função determinística sem efeitos colaterais (cálculo, validação, transformação), teste unitário é mais rápido, mais preciso sobre qual regra quebrou, e não exige montar todo o sistema para validar uma regra isolada.

## Como aplicar a checklist na prática (formato de saída)

Ao revisar uma mudança, estruture a resposta assim, sem pular itens:

```markdown
## Revisão TDD: [nome da task/mudança]

### Critérios de aceitação
[lista, ou nota de que precisam ser esclarecidos antes de continuar]

### Casos de teste definidos
[lista com tipo: feliz/borda/erro]

### Status dos testes
[passando / falhando / ausente — para cada caso listado acima]

### Checklist de revisão
- Comportamento testado: [sim/não + justificativa]
- Casos de borda cobertos: [sim/não + quais faltam]
- Implementação mínima: [sim/não + o que está além do necessário]
- Acoplamento introduzido: [sim/não + onde]
- Erros tratados: [sim/não + quais faltam]
- Nomenclatura clara: [sim/não + o que renomear]
- Seguro de alterar depois: [sim/não + por quê]

### Veredito
[aprovado / aprovado com ressalvas / bloqueado — e o motivo específico]

### Resumo do que mudou
[resumo objetivo, incluindo o que ficou fora do escopo]
```

## Sinais de alerta de que a disciplina está sendo pulada

- Implementação foi escrita antes de qualquer teste existir
- Teste foi escrito depois do código e passa de primeira, sem nunca ter sido visto falhando
- Refatoração e implementação de comportamento novo estão misturadas no mesmo commit/mudança
- A aprovação se baseia em rodar manualmente uma vez e "parecer certo"
- Casos de borda foram mencionados na conversa mas não têm teste correspondente
- O código trata casos hipotéticos que não estavam nos critérios de aceitação

Qualquer um desses sinais significa: pare a aprovação, volte para a etapa correspondente do workflow, e só então retome.
