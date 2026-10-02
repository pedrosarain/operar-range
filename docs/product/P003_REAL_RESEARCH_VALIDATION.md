# PRODUCT-03 — Real Research Validation

## Status da unidade

VALIDAÇÃO CONCLUÍDA COM FALHAS REGISTRADAS.

O PRODUCT-03 teve como objetivo validar operacionalmente, sem criação de novas funcionalidades e sem correção de defeitos, o fluxo real:

Dataset → Research → Experimentos → Perguntas → Resultado → Analytics

A execução utilizou dados reais já existentes no Operar Range.

---

## Evidências principais

### Dataset utilizado

- Dataset ID: `DS-D4E2397FAB4709EB`
- Mercado: `B3`
- Ativo: `WINV26`
- Período disponível: `2026-08-18` a `2026-08-19`
- Pregões: `2`
- Status: `READY`
- Research ready: `TRUE`

### Estratégia utilizada

- Modelo: `US_OPEN_BREAKOUT_V1`
- Estratégia: `TRADE_1`
- Status do modelo: `ACTIVE`

### Research criada

- Research ID: `RES-20261002T155522Z-88f1a9ac45c6`
- Nome: `PRODUCT-03 REAL RESEARCH VALIDATION`
- Dataset: `DS-D4E2397FAB4709EB`
- Mercado: `B3`
- Ativo: `WINV26`
- Período: `2026-08-18` a `2026-08-19`
- Status final: `COMPLETED`
- Lineage match: `TRUE`
- Execution units: `2`
- Batches: `1`

### Experimentos

- Experimentos gerados: `1`
- Experimentos válidos: `1`
- Experimentos inválidos: `0`
- Experimento utilizado: `EXP-000048`

A execução percorreu as etapas:

- PREPARING
- EXPERIMENT_GENERATOR
- CONSTRAINT_ENGINE
- BATCH_PLANNER
- DISTRIBUTED_EXECUTOR
- LINEAGE_ADAPTER
- ANALYTICS
- TRADE_LIFECYCLE_ANALYTICS
- RANKING
- COMPLETED

---

# PASS / FAIL por etapa

## Validação 1 — Importação / disponibilidade do Dataset

**PASS**

Validado:

- Dataset disponível;
- identidade preservada;
- Dataset selecionável;
- status READY;
- Dataset preparado para Research.

---

## Validação 2 — Criação de Research

**PASS**

Validado:

- criação de nova Research;
- geração de Research ID;
- dataset_id preservado;
- lineage preparado;
- estado inicial `CREATED`.

Research criada:

`RES-20261002T155522Z-88f1a9ac45c6`

---

## Validação 3 — Execução

**PASS**

Validado:

- início;
- progresso;
- conclusão;
- persistência dos artifacts;
- status final `COMPLETED`;
- lineage match `TRUE`.

---

## Validação 4 — Experimentos

**PASS**

Validado:

- experimento produzido;
- experimento persistido;
- experimento disponível na Research;
- Research selecionável;
- navegação contratual existente.

Experimento:

`EXP-000048`

---

## Validação 5 — Perguntas

**FAIL**

As perguntas obrigatórias não puderam ser respondidas pelo fluxo da nova Research:

- Quantos trades atingiram 100 pontos?
- Quantos atingiram 175?
- Quantos atingiram 200?
- Quantos voltaram ao zero?
- Quantos tomaram stop?
- Quantos atingiram target antes do stop?

### Evidência

Os loaders utilizados pela interface retornaram DataFrames vazios:

- `load_path_target_analytics`
- `load_path_stop_analytics`
- `load_path_target_stop_matrix`

A nova Research concluída não possui os artifacts de path analytics esperados por esses loaders.

Nenhuma correção foi realizada, conforme escopo do PRODUCT-03.

---

## Validação 6 — Drill-down

**FAIL**

Fluxo esperado:

Resposta  
↓  
Pregões  
↓  
Pregão  
↓  
Trajectory

### Evidência

As chamadas de drill-down falharam porque:

`path_analysis.parquet not found for Research RES-20261002T155522Z-88f1a9ac45c6`

Falharam:

- `get_session_detail`
- `resolve_trajectory`

Entretanto, a trajectory quantitativa física existe e foi validada diretamente:

- Data: `2026-08-18`
- trajectory_exists: `TRUE`
- linhas: `544960`
- arquivo presente: `TRUE`
- MFE: `1020`
- MAE: `1310`

Portanto, o problema observado é de disponibilidade/integração dos artifacts exigidos pelo fluxo de Perguntas e drill-down da interface, e não ausência da trajetória quantitativa base.

Nenhuma correção foi realizada.

---

## Validação 7 — Resultado / Conclusões / Analytics

**PASS**

Validado:

- Research concluída;
- resultados persistidos;
- métricas persistidas;
- métricas mensais persistidas;
- métricas anuais persistidas;
- rankings persistidos;
- experimento consistente entre artifacts.

Não existe conclusão formal persistida para esta Research.

A interface deve permanecer não inferencial e não criar conclusão automaticamente.

---

## Validação 8 — Dashboard

**PASS**

Após a execução, o Dashboard passou a refletir automaticamente:

- nova Research;
- status `COMPLETED`;
- Dataset utilizado;
- contagem de experimentos;
- Research como última concluída;
- métricas disponíveis.

---

## Validação 9 — Estratégias

**PASS**

A nova Research aparece vinculada à estratégia existente `TRADE_1`.

A biblioteca de Estratégias identificou a Research:

`RES-20261002T155522Z-88f1a9ac45c6`

---

## Validação 10 — Analytics

**PASS**

Validado para a nova Research:

- Geral;
- Períodos;
- Rankings.

Artifacts encontrados:

- Overall metrics: 1 linha para `EXP-000048`
- Monthly metrics: 1 linha
- Yearly metrics: 1 linha
- Rankings: 10 linhas para o experimento

---

# Resultado consolidado

| Validação | Resultado |
|---|---|
| 1 — Dataset | PASS |
| 2 — Criação de Research | PASS |
| 3 — Execução | PASS |
| 4 — Experimentos | PASS |
| 5 — Perguntas | FAIL |
| 6 — Drill-down | FAIL |
| 7 — Resultado / Conclusões / Analytics | PASS |
| 8 — Dashboard | PASS |
| 9 — Estratégias | PASS |
| 10 — Analytics | PASS |

Resultado:

**8 PASS / 2 FAIL**

---

# Problemas encontrados

## P03-01 — Path Analytics ausente na nova Research

A Research é executada integralmente e termina como `COMPLETED`, mas os artifacts consumidos pela área de Perguntas não são produzidos/disponibilizados no workspace da nova Research.

Impacto:

- perguntas quantitativas de path não respondem;
- loaders retornam vazios.

Nenhuma correção realizada nesta unidade.

---

## P03-02 — Drill-down depende de `path_analysis.parquet`

O drill-down da interface não consegue abrir o detalhe do pregão porque `path_analysis.parquet` não está disponível para a nova Research.

Impacto:

- Resposta → Pregões → Pregão → Trajectory não funciona integralmente.

A trajectory física existe e permanece íntegra.

Nenhuma correção realizada nesta unidade.

---

# Sugestões de UX

As sugestões abaixo não foram implementadas.

1. Quando Perguntas não possuir os artifacts necessários, apresentar mensagem explícita informando que a Research foi concluída, porém o módulo de análise de trajetória não está disponível para aquela execução.

2. Evitar respostas vazias que possam parecer ausência estatística quando, na realidade, o artifact necessário não foi produzido.

3. No drill-down, distinguir visualmente:
   - “não existem pregões compatíveis”;
   - “artifact de análise não disponível”.

4. Exibir no resumo da Research quais módulos analíticos estão disponíveis para aquela execução.

Estas são somente observações de experiência de uso.

---

# Integridade do PRODUCT-03

Durante esta unidade:

- nenhuma regra quantitativa foi alterada;
- nenhum algoritmo foi alterado;
- nenhum Dataset foi alterado;
- nenhum pipeline foi alterado;
- nenhuma nova funcionalidade foi criada;
- nenhuma tela foi criada;
- nenhum novo cálculo foi criado;
- nenhum ranking foi criado;
- nenhuma métrica foi criada;
- os defeitos encontrados não foram corrigidos.

O PRODUCT-03 é uma unidade exclusivamente de validação operacional.
