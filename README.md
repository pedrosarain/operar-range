# Operar Range Quant — v0.2

Fundação executável do motor de pesquisa quantitativa para o setup da abertura dos EUA.

## Já implementado
- abertura regular de NY derivada por timezone oficial (`America/New_York` -> `America/Sao_Paulo`);
- cálculo automático do último candle M5 pré-abertura;
- regra de entrada do Trade 1:
  - compra = máxima do candle de referência + 20 pontos;
  - venda = mínima do candle de referência - 20 pontos;
  - se a máxima/mínima do candle também for a máxima/mínima intraday até aquele momento, usar 40 pontos;
- contrato mínimo de dados de ticks;
- testes automatizados de calendário e da regra 20/40;
- arquivo `.replit` e `main.py` para abrir no Replit e clicar **Run**.

## O que deliberadamente ainda NÃO está fechado
A execução completa de Trade 1/Trade 2 será validada contra um pregão real de WIN e contra a planilha manual antes de escalar.

## Próximo marco
Receber um pregão completo de WIN em ticks, importar, reconstruir candles e comparar um dia conhecido com o backtest manual.
