# PRODUCT-05 — Quantitative Validation Against Current Dataset

## Identidade

- Research utilizada: `RES-20261006T190353Z-a6674069a68d`
- Dataset: `DS-D4E2397FAB4709EB`
- Experiment ID: `EXP-000048`
- Modelo: `US_OPEN_BREAKOUT_V1` / `US OPEN BREAKOUT V1`
- Período: `2026-08-18` → `2026-08-19`
- Baseline de código: `f33ec114a2c8f8056ca4b42f47ef6d8ef962d1f5`

## Objetivo

Validar a consistência quantitativa interna do Operar Range sobre o dataset atualmente disponível.

A pergunta desta unidade é:

> Todos os módulos quantitativos do Operar Range respondem exatamente a mesma verdade para o mesmo dataset?

Esta unidade não compara os resultados contra o estudo manual de 164 pregões.

## Escopo validado

- Targets: 100, 125, 150, 175, 200, 250, 300, 350, 400, 500, 600, 800 e 1000.
- Relações com primeiro retorno ao zero.
- Todas as combinações Target × Stop existentes.
- Stops antes de qualquer target.
- Stops antes de target específico.
- Trade 2: eligible, occurred, executed, positive, negative e break-even.
- Drill-down contra Session Detail.
- Identidade de entrada do Path Analysis contra Trajectory.

## Módulos quantitativos comparados

- Path Analysis
- Path Aggregation
- Question Layer / Path Query / Drill-down
- Session Detail
- Trajectory
- Trade 2 Analytics
- Experiment Metrics
- Distributed Experiment Results

## Observação semântica — Lifecycle Analytics

Durante a auditoria foi detectada uma comparação semanticamente inválida entre `trade2_winning_count` e `winning_cycles`.

`trade2_winning_count` representa exclusivamente resultados positivos do Trade 2.

`winning_cycles` representa ciclos consolidados vencedores de Trade 1 + Trade 2 e pertence a outro domínio estatístico.

Portanto, `winning_cycles` não foi utilizado como fonte para a pergunta **Trade 2 positive**.

A validação correta dessa pergunta utilizou:

- Distributed Experiment Results
- Trade 2 Analytics
- Experiment Metrics
- Question Layer

Todas retornaram `0`.

Nenhum código, regra, metodologia ou algoritmo foi alterado em decorrência dessa auditoria.

## Resultado consolidado

- Perguntas respondidas: **260**
- MATCH: **260**
- DIVERGENT: **0**

## Relatório de divergências

Nenhuma divergência quantitativa válida encontrada.

## Relatório completo de comparação

| Pergunta | Origens | Resultados | Status |
|---|---|---|---|
| Target 100 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 125 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 150 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 175 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 200 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 250 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 300 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 350 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 400 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 500 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 600 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 800 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 1000 atingido | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 100 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 100 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 100 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 125 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 125 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 125 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 150 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 150 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 150 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 175 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 175 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 175 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 200 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 200 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 200 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 250 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 250 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 250 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 300 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 300 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 300 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 350 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 350 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 350 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 400 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 400 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 400 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 500 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 500 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 500 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 600 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 600 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 600 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 800 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 800 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 800 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 1000 antes do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 1000 depois do primeiro retorno ao zero | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 1000 atingido e posteriormente retorno ao zero | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Target 100 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 100 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 100 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 100 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 100 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 100 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 100 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 100 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 100 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 100 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 125 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 125 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 125 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 125 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 125 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 125 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 125 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 125 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 125 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 125 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 150 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 150 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 150 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 150 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 150 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 150 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 150 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 150 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 150 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 150 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 175 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 175 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 175 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 175 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 175 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 175 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 175 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 175 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 175 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 175 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 200 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 200 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 200 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 200 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 200 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 200 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 200 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 200 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 200 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 200 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 250 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 250 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 250 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 250 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 250 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 250 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 250 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 250 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 250 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 250 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 250 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 250 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 250 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 250 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 250 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 300 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 300 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 300 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 300 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 300 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 300 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 300 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 300 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 300 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 300 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 300 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 300 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 300 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 300 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 300 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 350 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 350 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 350 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 350 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 350 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 350 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 350 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 350 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 350 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 350 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 350 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 350 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 350 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 350 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 350 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 400 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 400 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 400 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 400 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 400 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 400 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 400 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 400 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 400 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 400 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 400 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 400 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 400 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 400 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 400 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 500 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 500 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 500 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 500 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 500 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 500 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 500 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 500 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 500 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 500 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 500 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 500 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 500 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 500 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 500 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 600 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 600 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 600 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 600 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 600 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 600 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 600 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 600 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 600 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 600 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 600 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 600 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 600 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 600 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 600 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 800 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 800 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 800 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 800 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 800 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 800 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 800 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 800 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 800 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 800 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 800 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 800 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 800 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 800 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 800 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 1000 antes do stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes do target 1000 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 1000 atingido e depois stop 100 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 1000 antes do stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 125 antes do target 1000 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 1000 atingido e depois stop 125 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 1000 antes do stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 150 antes do target 1000 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 1000 atingido e depois stop 150 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 1000 antes do stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 175 antes do target 1000 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 1000 atingido e depois stop 175 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Target 1000 antes do stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 200 antes do target 1000 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 0<br>0<br>0 | **MATCH** |
| Target 1000 atingido e depois stop 200 | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down | 1<br>1<br>1 | **MATCH** |
| Stop 100 antes de qualquer target | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Stop 125 antes de qualquer target | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Stop 150 antes de qualquer target | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Stop 175 antes de qualquer target | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Stop 200 antes de qualquer target | Path Aggregation<br>Question Layer / Drill-down | 0<br>0 | **MATCH** |
| Drill-down target sessions vs Session Detail | Drill-down sessions checked<br>Session Detail matches | 13<br>13 | **MATCH** |
| Path Analysis entry identity vs Trajectory | Path Analysis sessions<br>Trajectory entry matches | 1<br>1 | **MATCH** |
| Trade 2 eligible | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down<br>Trade 2 Analytics | 0<br>0<br>0<br>0 | **MATCH** |
| Trade 2 occurred | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down<br>Trade 2 Analytics | 0<br>0<br>0<br>0 | **MATCH** |
| Trade 2 executed | Path Aggregation<br>Path Analysis<br>Question Layer / Drill-down<br>Trade 2 Analytics | 0<br>0<br>0<br>0 | **MATCH** |
| Trade 2 positive | Experiment Metrics<br>Question Layer<br>Raw Distributed Results<br>Trade 2 Analytics | 0<br>0<br>0<br>0 | **MATCH** |
| Trade 2 negative | Lifecycle Analytics<br>Trade 2 Analytics | 0<br>0 | **MATCH** |
| Trade 2 break-even | Lifecycle Analytics<br>Trade 2 Analytics | 0<br>0 | **MATCH** |

## Gates

- Research criada e executada: PASS
- Research concluída: PASS
- Question artifacts: PASS
- Validação cruzada: PASS
- Dataset immutability: PASS
- Nenhuma metodologia alterada: TRUE
- Nenhum algoritmo alterado: TRUE
- Nenhum dataset alterado: TRUE
- Nenhuma regra quantitativa alterada: TRUE

## Conclusão

Para o dataset atual e para as 260 perguntas auditadas, os componentes quantitativos comparáveis da plataforma produziram resultados consistentes entre si.

**PRODUCT05=PASS**
