# PRODUCT-01 — Research Workspace V2

## Status

HOMOLOGADO

---

# Objetivo

Formalizar a interface oficial do laboratório quantitativo Operar Range.

O PRODUCT-01 foi criado para transformar a interação com o laboratório em uma experiência orientada por pesquisa, preservando integralmente o backend quantitativo já homologado.

---

# Contexto

Na homologação do PRODUCT-01 o backend quantitativo encontrava-se operacionalmente consolidado.

Os motores quantitativos, datasets, pipeline de pesquisa, lineage e mecanismos de execução já produziam evidências quantitativas válidas.

O problema existente era exclusivamente de experiência de uso.

O pesquisador precisava navegar por artefatos técnicos para responder perguntas quantitativas.

O PRODUCT-01 reorganiza apenas a camada de apresentação.

Nenhuma evidência quantitativa passou a ser produzida pela interface.

---

# Princípios

- Pesquisa é a unidade central do laboratório.
- A interface deve responder perguntas quantitativas.
- O pesquisador não precisa conhecer componentes internos.
- A Presentation Layer nunca produz evidência quantitativa.
- O backend permanece como única fonte da verdade.

---

# Navegação Oficial

As únicas rotas públicas homologadas são:

- Dashboard
- Pesquisas
- Estratégias
- Analytics
- Administração

---

# Estrutura Oficial da Pesquisa

Cada Pesquisa possui as seguintes abas oficiais:

- Resumo
- Perguntas
- Resultado
- Experimentos
- Analytics
- Conclusões

Essas áreas pertencem à Pesquisa e não representam novas rotas públicas.

---

# Laboratório de Perguntas

Perguntas passa a ser o mecanismo oficial de interação entre pesquisador e motor quantitativo.

Fluxo oficial:

Pergunta

↓

Resposta

↓

Drill-down

↓

Pregão

↓

Trajectory

---

# Interface Pública

Deixam de fazer parte da navegação pública:

- hashes
- manifests
- registry
- runtime
- paths
- query engines
- artifacts técnicos

Esses elementos permanecem internos ao laboratório.

---

# Separação de Responsabilidades

Presentation Layer

×

Quant Engine

A camada de produto nunca cria:

- hipótese confirmada
- edge
- melhor estratégia
- melhor stop
- descoberta quantitativa

Essas informações somente podem existir quando produzidas formalmente pelo backend quantitativo.

---

# Critérios de Aceite

A homologação do PRODUCT-01 exigiu:

- manutenção integral do backend quantitativo;
- nenhuma alteração metodológica;
- nenhuma alteração em datasets;
- nenhuma alteração em lineage;
- nenhuma alteração em pipeline;
- nenhuma alteração em engine;
- migração completa para o Research Workspace V2;
- Dashboard factual;
- Pesquisa como unidade central do laboratório;
- cinco rotas públicas oficiais.
