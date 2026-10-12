# PRODUCT-07 — Register First Official Manual Baseline

## Objetivo

O PRODUCT-07 registra o primeiro Manual Baseline Oficial do Operar Range.

A unidade utiliza exclusivamente artefatos quantitativos originais explicitamente aprovados pelo fundador/CTO.

Não existe comparação entre Manual Baseline e Research nesta unidade.

## Decisão institucional

Um Manual Baseline representa um estudo quantitativo.

Ele pode ser composto por um ou mais arquivos independentes, desde que pertençam ao mesmo estudo e tenham sido explicitamente aprovados como seus componentes.

Documentação administrativa, ADRs, READMEs e documentação técnica do projeto não integram um Manual Baseline.

## Primeiro Manual Baseline

O único componente aprovado para a versão inicial é:

`data/manual/candle18_manual.xlsx`

SHA-256 original aprovado:

`d83dfa42a7a3956301af112809ea02bb507176d312085f7c2788b3e089fdc33e`

Nenhum outro arquivo foi autorizado para a versão inicial.

## Preservação

Cada componente do Manual Baseline preserva:

- ordem documental;
- nome original;
- nome persistido;
- tipo;
- extensão;
- tamanho em bytes;
- SHA-256 individual.

Os arquivos não são:

- fundidos;
- alterados;
- recalculados;
- reinterpretados;
- reescritos.

## Identidade do conjunto

Além do `baseline_sha256` já definido no PRODUCT-06, o contrato composto possui:

- `component_count`;
- `components`;
- `components_schema_version`;
- `components_sha256`.

`components_sha256` identifica deterministicamente o conjunto documental da versão.

O `baseline_sha256` continua identificando o conteúdo institucional completo daquela versão do Manual Baseline.

## Versionamento

O contrato homologado no PRODUCT-06 permanece válido.

A inclusão futura de novos componentes no mesmo estudo exige nova versão.

Nenhuma versão existente poderá ser sobrescrita.

## Interface

A área:

`Administração → Dados → Manual Baselines`

permanece somente leitura.

Passa também a apresentar a quantidade de componentes e o hash institucional dos componentes registrados.

## Fora do escopo

O PRODUCT-07 não implementa:

- comparação com Research;
- MATCH;
- DIVERGENT;
- validação quantitativa;
- Analytics;
- Queries;
- IA;
- novos motores;
- alterações de metodologia.

---

## Registro oficial realizado

O primeiro Manual Baseline Oficial foi registrado.

- Baseline ID: `MBL-763E34D105F0BD82`
- Nome: `US OPEN BREAKOUT V1 Manual Baseline Oficial`
- Versão: `1`
- Status: `OFFICIAL`
- Estratégia: `US OPEN BREAKOUT V1`
- Mercado: `B3`
- Ativo: `WINFUT`
- Período: `2026-01-01` a `2026-09-21`
- Pregões: `164`
- Componentes: `1`
- Data de registro: `2026-10-12T19:34:49Z`
- Components SHA-256: `0520fcd449743f48a03c4dc499dbe6821b0ea4b43a813b02c5548259542d95ef`
- Baseline SHA-256: `a6f757e593e4ba98ca782b768a7064144f9a0548c2dc591421af03f42e046e4c`

### Componente preservado

- Nome original: `candle18_manual.xlsx`
- Nome persistido: `candle18_manual.xlsx`
- Tipo: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Extensão: `.xlsx`
- Tamanho: `47307` bytes
- SHA-256: `d83dfa42a7a3956301af112809ea02bb507176d312085f7c2788b3e089fdc33e`

O componente persistido é byte a byte idêntico ao arquivo original aprovado.

As respostas quantitativas existentes permanecem preservadas no XLSX original.

Nenhum valor foi recalculado, reinterpretado ou corrigido durante o registro.

Nenhuma comparação com Research foi executada.
