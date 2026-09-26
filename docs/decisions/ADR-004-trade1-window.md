# ADR-004 — Janela de validade do Trade 1

## Status

Aprovada.

## Decisão

Na Fase 1 do Operar Range, o Trade 1 somente existe quando o rompimento do candle de referência ocorre no candle de 5 minutos imediatamente seguinte.

Exemplo com NY Open às 10:30:

- candle de referência: 10:25–10:30;
- candle válido para entrada: 10:30–10:35.

A janela é fechada no limite superior:

- timestamps >= 10:30 são elegíveis;
- timestamps < 10:35 são elegíveis;
- timestamp exatamente 10:35 não é elegível.

Se nenhum dos níveis de entrada for rompido dentro dessa janela:

- registrar `SEM TRADE 1`;
- encerrar a procura pela entrada do Trade 1 naquele pregão;
- não procurar rompimentos posteriores.

No horário de verão, aplica-se a mesma lógica:

- candle de referência: 11:25–11:30;
- candle válido para entrada: 11:30–11:35.

## Motivação

Esta regra reproduz fielmente o operacional utilizado no estudo manual da Fase 1.

## Restrições

Nesta fase:

- a janela não é parametrizável;
- não existem alternativas de duração;
- não se procura entrada após o candle imediatamente seguinte.

A parametrização poderá ser tratada posteriormente na fase de pesquisa quantitativa.