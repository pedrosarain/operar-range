# Etapa 1 — Requisitos de dados (v0.1)

## Objetivo imediato
Receber uma amostra real pequena e provar, dia a dia, que o motor reconstrói o mesmo Trade 1 e Trade 2 da planilha manual.

## Granularidade exigida para a fase de validação
**Ticks de negócios (trades) são a preferência e o padrão inicial.**

M1 pode ser usado depois para cálculos que não dependam da ordem intrabar. Para validar rompimento, stop, alvo, 0x0 e reentrada quando dois níveis podem ocorrer dentro do mesmo minuto, OHLC M1 sozinho pode ser ambíguo. Não aceitaremos inventar a ordem dos eventos.

## Campos mínimos por negócio
1. `timestamp` com data, hora e fuso claramente documentados; idealmente UTC e precisão de milissegundo ou melhor.
2. `symbol` / código exato do contrato (ex.: contrato individual de WIN, não apenas um rótulo genérico).
3. `price` do negócio.
4. `quantity`/volume do negócio — desejável e deve ser solicitado.
5. identificador/sequência do negócio — desejável para desempatar negócios com mesmo timestamp.

## Metadados necessários
- timezone original do feed;
- precisão do timestamp;
- política de correções/cancelamentos de negócios;
- calendário/cobertura histórica;
- identificação dos contratos e vencimentos;
- definição de qualquer série contínua fornecida;
- informação sobre ajustes/back-adjustment, se houver;
- formato do arquivo e compressão.

## Contratos x série contínua
Para o motor de pesquisa, preferimos **contratos individuais de WIN com seus códigos e vencimentos**. Assim construímos a regra de contrato ativo de forma transparente.

Se o fornecedor também oferecer uma série contínua equivalente ao `WINFUT`, ela é útil para comparação com o estudo feito no Profit, mas precisamos saber exatamente como essa série é construída e se existe ajuste histórico de preços.

## Amostra ideal para começar
Não precisamos comprar anos de dados antes da prova técnica. Solicitar primeiro uma amostra de ticks cobrindo pelo menos estes dias de 2026 (pregão completo, não só 10:30):

- 05/01/2026 — Trade 1 LOSS; reentrada manual registrada.
- 20/01/2026 — Trade 1 LOSS; reentrada manual registrada.
- 04/03/2026 — Trade 1 LOSS; Trade 2 com corrida grande.
- 12/03/2026 — Trade 1 LOSS; Trade 2 com corrida grande.
- 14/04/2026 — Trade 1 LOSS; reentrada com retorno ao 0x0 e sem stop 170 na anotação manual.

Adicionar também 2 ou 3 dias de WIN simples para validar o caminho sem reentrada.

## Horário da abertura dos EUA
O software não terá uma tabela manual de “10:30 ou 11:30”. A regra base será:

`09:30 America/New_York -> converter para America/Sao_Paulo`

Isso resolve automaticamente a diferença de horário de verão. Depois adicionaremos uma camada de calendário oficial da sessão americana para feriados e sessões especiais.

## Critério de aceitação da amostra
A amostra só é considerada adequada se conseguirmos:
- ordenar eventos sem ambiguidade relevante;
- reconstruir candles M5;
- saber qual contrato está sendo analisado;
- localizar o candle imediatamente anterior a 09:30 NY;
- identificar qual lado rompeu primeiro;
- reproduzir stop/alvo/0x0/reentrada em casos conhecidos.
