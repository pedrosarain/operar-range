# PRODUCT-06 — Official Manual Baseline Registry

## Objetivo

O PRODUCT-06 estabelece a infraestrutura institucional para registrar estudos quantitativos produzidos manualmente como **Manual Baselines** oficiais do Operar Range.

Nesta unidade não existe importação de planilha, comparação automática, cálculo quantitativo ou validação científica.

A infraestrutura criada existe para permitir que esses processos sejam implementados posteriormente sem confundir um estudo manual com as demais entidades da plataforma.

---

## Manual Baseline

Uma **Manual Baseline** representa um estudo quantitativo produzido manualmente e preservado como referência oficial para futuras validações.

É uma entidade própria do Operar Range.

Uma Manual Baseline:

- não é uma Research;
- não é um Dataset;
- não é um Experiment;
- não executa motores quantitativos;
- não produz Analytics;
- não executa Queries;
- não altera dados de mercado.

Seu propósito é preservar uma referência externa/manual de forma versionada, auditável e imutável por versão.

---

## Identidade

Cada Manual Baseline possui, no mínimo:

- Baseline ID;
- nome;
- descrição;
- estratégia;
- mercado;
- ativo;
- Dataset de origem, quando conhecido;
- universo analisado;
- quantidade de pregões;
- autor;
- data de criação;
- status;
- observações;
- versão;
- hash SHA-256;
- versão do Registry;
- versão do schema;
- estrutura de resultados oficiais.

O identificador utiliza o prefixo:

`MBL-`

---

## Dataset de origem

Uma Manual Baseline pode referenciar um Dataset conhecido através de:

`source_dataset_id`

Esse vínculo não transforma a Manual Baseline em Dataset.

A ausência de Dataset de origem conhecido é permitida.

---

## Versionamento

Cada revisão de uma Manual Baseline é persistida como uma nova versão.

O contrato de armazenamento é:

`data/manual/baselines/<BASELINE_ID>/versions/<VERSION>.json`

Exemplo conceitual:

`data/manual/baselines/MBL-XXXXXXXXXXXXXXX/versions/000001.json`

Versões existentes são imutáveis.

Uma revisão futura deverá criar uma nova versão e preservar integralmente as anteriores.

Cada versão possui:

- número da versão;
- data;
- autor;
- hash SHA-256.

---

## Hash

Cada versão possui `baseline_sha256`.

O hash representa o conteúdo canônico da versão da Manual Baseline.

O hash existe para permitir auditoria de integridade e identificação de alterações entre versões.

---

## Resultados oficiais

A infraestrutura permite armazenar respostas oficiais da Manual Baseline sem impor cálculos ou métricas novas.

Cada resposta possui contrato genérico com:

- `question_key`;
- `question_label`;
- `category`;
- `value_type`;
- `value`;
- `unit`;
- `dimensions`;
- `notes`.

Categorias inicialmente suportadas pelo contrato:

- TARGET;
- ZERO_RELATION;
- TARGET_STOP;
- STOP_TARGET;
- TRADE_2;
- EXPECTANCY;
- WIN_RATE;
- DRAWDOWN;
- OTHER.

A existência dessas categorias não implementa cálculos.

Elas apenas estruturam resultados que poderão ser registrados futuramente.

Exemplos conceituais de perguntas futuras:

- Target 100;
- Target 125;
- Target 150;
- Target 175;
- Target 200;
- Target antes do primeiro retorno ao zero;
- Target depois do primeiro retorno ao zero;
- Target → Stop;
- Stop → Target;
- Trade 2;
- Expectancy;
- Win Rate;
- Drawdown.

Nenhum valor real foi registrado no PRODUCT-06.

---

## Separação de entidades

### Dataset

Representa o universo de dados de mercado utilizado pela plataforma.

### Research

Representa uma pesquisa quantitativa executável e possui identidade e lineage próprios.

### Experiment

Representa uma configuração quantitativa executada dentro do processo de Research.

### Manual Baseline

Representa uma referência quantitativa produzida manualmente e registrada institucionalmente.

Esses quatro conceitos não são intercambiáveis.

---

## Contrato para comparação futura

O PRODUCT-06 prepara somente o contrato estrutural necessário para uma futura comparação:

Research
↓
Manual Baseline
↓
MATCH ou DIVERGENT

O contrato prevê os campos:

- `research_id`;
- `manual_baseline_id`;
- `manual_baseline_version`;
- `manual_baseline_sha256`;
- `question_key`;
- `research_value`;
- `manual_baseline_value`;
- `status`.

Status previstos:

- `MATCH`;
- `DIVERGENT`.

A comparação não está implementada nesta unidade.

O contrato está explicitamente marcado como:

`CONTRACT_ONLY`

---

## Administração

A área **Administração → Dados** passa a possuir:

`Manual Baselines`

Nesta unidade a área é somente leitura.

Ela lista Baselines existentes e apresenta, quando disponíveis:

- Baseline ID;
- nome;
- estratégia;
- mercado;
- ativo;
- quantidade de pregões;
- autor;
- versão;
- status;
- hash.

Não existe nesta unidade:

- criação pela interface;
- edição;
- importação;
- exclusão;
- comparação;
- cálculo.

---

## Persistência

Nenhum registro real de Manual Baseline é criado pelo PRODUCT-06.

O diretório institucional somente passa a ser utilizado quando uma Manual Baseline real for registrada em etapa posterior.

Os testes utilizam armazenamento temporário e dados sintéticos exclusivamente para validar o contrato técnico.

---

## Fora do escopo

O PRODUCT-06 não implementa:

- importação da planilha manual;
- comparação automática;
- Analytics;
- Queries;
- IA;
- novos motores quantitativos;
- novas métricas;
- validação científica;
- alteração de metodologia;
- alteração de regras quantitativas.

---

## Responsabilidade

A responsabilidade do Manual Baseline Registry é exclusivamente:

1. preservar identidade;
2. preservar metadata;
3. preservar resultados fornecidos;
4. preservar histórico de versões;
5. preservar integridade por hash;
6. disponibilizar leitura institucional;
7. fornecer contrato para comparação futura.

Ele não interpreta resultados e não decide se uma Research é correta.

---

## Estado ao final do PRODUCT-06

Ao final desta unidade, o Operar Range possui infraestrutura permanente para registrar Manual Baselines oficiais sem misturá-las com Dataset, Research ou Experiment.

A ingestão do estudo manual real permanece para unidade posterior.
