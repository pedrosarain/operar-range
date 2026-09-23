# Ambiguidades operacionais que ainda precisam ser fechadas

Estas regras **não impedem a Etapa 1 de dados** e não serão inventadas. Vamos fechá-las durante a reprodução dos primeiros dias, usando gráfico/planilha e o dado bruto.

1. **Preço exato de disparo no rompimento**
   - entrada quando negocia exatamente na máxima/mínima do candle de referência, ou somente 1 tick além?
   - em gap/ salto de preço, fill é no nível teórico ou no primeiro negócio disponível?

2. **Se os dois lados do candle de referência forem rompidos**
   - direção é sempre o primeiro rompimento cronológico; ticks permitirão resolver a ordem.

3. **Regra precisa do “candle contra” que invalida o Trade 2**
   - precisamos formalizar qual candle é observado e qual nível precisa ser rompido.

4. **Horizonte do runner / condução por candle**
   - definir até que horário o trade pode permanecer aberto e a regra exata de saída por rompimento de candle contrário.

5. **Empates de stop/alvo/0x0**
   - com ticks a ordem real resolve a maioria dos casos; ainda precisamos definir igualdade exata do nível e política de execução.

6. **Contrato usado no estudo manual**
   - confirmar se a planilha foi observada no gráfico contínuo `WINFUT` do Profit ou no contrato vigente do dia. Isso será confrontado com o fornecedor e com os primeiros casos.
