# Engenharia reversa: carteira `0x0812…f45d`

`0x0812f31ccf62c48e6da3da3fbf98663779e1f45d` · [CoinGlass](https://www.coinglass.com/hyperliquid/0x0812f31ccf62c48e6da3da3fbf98663779e1f45d) · dados até 14/out/2026

Fonte: API pública da Hyperliquid. A conta é nova (primeiro depósito em 3/ago/2026, primeiro trade em 20/ago) e a API entrega o histórico inteiro: 4.095 fills e 12 eventos de ledger. O PnL realizado nos fills (+US$ 55,0 mil), menos as taxas (−US$ 3,8 mil), mais o funding (+US$ 1,3 mil) e o não realizado (−US$ 0,2 mil), dá US$ 52,4 mil, o mesmo valor do `portfolio`. Tabelas e gráficos: [`relatorio_auto.md`](relatorio_auto.md). Os números que não estão lá vêm de [`analise_extra.py`](analise_extra.py).

---

## Resumo

- **Quem é:** um **trader manual e discricionário**, de conta pequena que cresceu rápido. Entraram **US$ 18,7 mil** (ago–set) e saíram US$ 3,8 mil para a HyperEVM. A conta tem hoje **US$ 67,3 mil**. São **+US$ 52,4 mil em 7 semanas, ~3,5x o capital líquido**. Opera pela interface e pelo app (ordens `FrontendMarket`, lotes redondos), todos os dias, das 5h às 22h UTC.
- **Antes disso, um bot de teste.** De 20 a 23/ago, o agente de API **"hermes-rail-live"** fez ~1.000 trades de **US$ 11** em rodízio BTC → ETH → SOL a cada ~4,5 minutos, alternando long e short e fechando ~14 segundos depois. O resultado foi −US$ 1 de preço e −US$ 4,6 de taxas. É um **teste de integração** de um sistema automático, não uma estratégia. Depois de 23/ago ele não aparece mais.
- **O que faz:** **vende alts que subiram muito** e, desde o fim de setembro, faz **swing de BTC e ETH nos dois lados**, com posições de 1 a 5 dias.
  - **Shorts de alts** (ARB, UNI, ZEC, XRP, LTC, NEAR, FARTCOIN, SOL, MON): entra depois de alta mediana de **+41% em 30 dias**, a ~4% da máxima. Rendeu **+US$ 19,0 mil**, quase tudo nas moedas que tinham subido mais de 30% (21 episódios, 67% com lucro).
  - **BTC/ETH:** +US$ 18,3 mil vendido e +US$ 13,6 mil comprado.
- **Gestão de risco: usa stop, e mexe nele.** Foram 413 ordens de gatilho em 33 dias, recolocadas em média 4 vezes por dia em cada moeda (stop móvel feito à mão), e 20 delas foram disparadas. Os stops começam em 4/set, logo depois das primeiras perdas grandes (UNI −US$ 4,2 mil e ARB −US$ 3,8 mil, com o preço até 26–41% contra).
- **O risco está no tamanho.** O nocional por trade subiu de ~US$ 15 mil (início de setembro) para **US$ 336 mil** (BTC, 11/out). A exposição bruta chegou a **14,6x o patrimônio** (4/out). O pior dia (8/out) custou **−US$ 15,8 mil**, e o recuo desde o pico foi de **−US$ 22 mil, 42% do patrimônio**. O lucro foi refeito em 5 dias.
- **Dá para replicar ou copiar?** **Não há base estatística.** São 7 semanas, 62 episódios relevantes e um mercado específico (alta forte das alts em set/2026). Espelhar a posição ainda funciona com 12h de atraso, mas o resultado desaba com 24–72h. A ideia replicável ("vender alt que subiu mais de 30% em 30 dias, com stop") já foi testada no universo inteiro na análise da [`0xfce0…`](../0xfce053a5e461683454bf37ad66d20344c0e3f4c0/ANALISE.md) e em [`regras_short.md`](../estudos/regras_short.md).

---

## 1. Quem é essa carteira

- **Duas API wallets (agentes):**
  - **`hermes-rail-live`** (`0x87fe…61d3`): pelo nome e pelo padrão, é um sistema automático em produção ("live") que foi ligado à conta e testado com o menor tamanho possível.
  - **`Mobile QR`** (`0x73a3…3bf4`): é o login do app de celular, feito com QR code a partir do site.
- **Fase 1, o bot (20–23/ago).** São 1.016 fills e 992 ordens, sempre de ~US$ 11,6 (logo acima do mínimo de US$ 10):
  - a sequência é BTC → ETH → SOL → BTC…, com uma abertura a cada 4,5 minutos (mediana);
  - o lado alterna em 84% das vezes (long, short, long…);
  - abre a mercado (100% *taker*) e fecha em ~14 segundos, 64% das vezes com limite *maker*;
  - resultado: −US$ 1,25 de preço e −US$ 4,56 de taxas em US$ 12,9 mil de volume.

  Não procura lucro. É o padrão de quem testa o caminho completo da ordem (abrir, confirmar, fechar) nos dois lados e em três mercados. Nenhuma ordem depois de 23/ago tem esse formato, mas o agente segue autorizado.
- **Fase 2, manual (de 27/ago em diante).** São 447 ordens em 7 semanas:
  - 91% do nocional é *taker*, com ordens `FrontendMarket` (a mercado pela interface) e limites `Ioc` do app;
  - os lotes são redondos: 2.500/5.000/10.000 NEAR, 0,5/1/4 BTC, 15/25/40/75 ETH;
  - as saídas parciais usam limites `reduceOnly` deixados no livro (227 colocados, 49 executados);
  - não usa `cloid`, que bots costumam preencher.
- **Horário.** As decisões se espalham das 5h às 22h UTC, com pico das 9h às 15h. Opera também nos fins de semana (dom. 14% das ordens). Não dá para inferir o fuso com segurança.
- **Dinheiro.**
  - **Entradas:** 8 envios, de US$ 42 (3/ago) a US$ 6,6 mil, somando US$ 18,7 mil até 5/set. Todos vêm da `0x6b9e…0a24`, a *hot wallet* de exchange ou ponte que também abasteceu a [`0xc7c3…`](../0xc7c37b0c7af5af560bf31b0bcbfec04b97361275/ANALISE.md) e a [`0xfce0…`](../0xfce053a5e461683454bf37ad66d20344c0e3f4c0/ANALISE.md). Ela atende centenas de usuários, então isso **não liga** as carteiras.
  - **Saídas:** só US$ 3,8 mil, para a HyperEVM. O resto do lucro é reinvestido.
  - **Conta unificada.** A margem fica no saldo spot de USDC (US$ 67,3 mil). Por isso o `clearinghouseState` de perps mostra só US$ 1,1 mil.
  - Existe uma subconta "Hedging" (`0xd2b2…c36d`), **vazia e nunca usada**.

## 2. De onde veio o PnL

**Por mês** (fase manual, PnL realizado):

| mês | realizado | taxas | volume | ordens |
|---|---|---|---|---|
| ago (27–31) | +US$ 0,4 mil | −US$ 17 | US$ 0,06M | 33 |
| set | +US$ 15,8 mil | −US$ 0,9 mil | US$ 2,26M | 233 |
| out (1–14) | +US$ 38,9 mil | −US$ 2,8 mil | US$ 6,92M | 181 |

**Por classe e lado** (soma dos episódios, de zerado a zerado):

|  | long | short |
|---|---|---|
| BTC/ETH | +US$ 13,6 mil (13 episódios) | +US$ 18,3 mil (11) |
| alts | +US$ 4,0 mil (11) | +US$ 19,0 mil (33) |

**A curva teve duas fases.** Até 14/set, o PnL acumulado foi a **−US$ 5,6 mil**, ou −30% do que tinha entrado. As perdas vieram de shorts em UNI, ARB e ZEC que continuaram subindo. Depois:

- o long de BTC e ETH de 16 a 21/set rendeu +US$ 10,2 mil;
- os shorts de LTC, NEAR, FARTCOIN, ARB e ETH entre 23/set e 7/out renderam ~+US$ 25 mil;
- o swing de BTC entre 8 e 14/out rendeu +US$ 12,1 mil.

**Episódios com nocional ≥ US$ 10 mil:** 62, com 53% de lucro. O ganho médio é de US$ 2,4 mil e a perda média de US$ 0,8 mil, uma relação de ~2,9:1 que é a assinatura de quem corta a perda com stop.

| lado | episódios | com lucro | soma | duração mediana |
|---|---|---|---|---|
| short | 42 | 62% | +US$ 37,8 mil | 1,4 dia |
| long | 20 | 35% | +US$ 17,0 mil | 0,06 dia |

Os longs são quase sempre tentativas curtas de pegar repique (muitas de minutos em 7/out). Perdem na maior parte das vezes, e o resultado positivo vem de três trades de dias: BTC e ETH de 16/set, BTC de 8/out e NEAR de 8/out.

## 3. O padrão de entrada nos shorts de alts

São 31 episódios com nocional ≥ US$ 10 mil. Medianas antes da primeira ordem:

| retorno 7d | retorno 30d | distância da máx. de 30d | funding a.a. nas 24h anteriores |
|---|---|---|---|
| +14,9% | +41,0% | −4,1% | 11% (a taxa-base da Hyperliquid) |

| moeda tinha subido em 30 dias | episódios | com lucro | soma |
|---|---|---|---|
| ≥ +30% | 21 | 67% | +US$ 19,0 mil |
| < +30% | 10 | 40% | +US$ 0,4 mil |

- **Vende força perto do topo.** A entrada acontece ~4% abaixo da máxima de 30 dias, depois de uma semana de alta. Exemplos: NEAR com +174% em 30 dias, ZEC com +140%, ARB com +143% e UNI com +100%.
- **Funding não é o gatilho.** Na maioria das entradas ele estava na taxa-base (~11% a.a.). Só MON (36%) e NEAR (27%) tinham compradores pagando caro. Isso difere da [`0xfce0…`](../0xfce053a5e461683454bf37ad66d20344c0e3f4c0/ANALISE.md), que escolhia memecoins com funding alto.
- **O preço contra é limitado pelo stop.** A partir de 7/set, o preço não andou mais de ~8% contra a primeira ordem em nenhum short de alt. Antes, ARB tinha andado 41% e UNI 26%.
- **Insiste na mesma moeda.** NEAR foi vendido 6 vezes em duas semanas, UNI 4 vezes e ARB 3 vezes. Quando o stop dispara, ele volta a vender mais alto.

## 4. Risco

- **O tamanho cresce com o lucro, mais rápido que o patrimônio:**

  | semana até | patrimônio (fim) | maior nocional bruto | alavancagem máx. |
  |---|---|---|---|
  | 6/set | US$ 10,8 mil | US$ 43 mil | 4,0x |
  | 13/set | US$ 13,9 mil | US$ 89 mil | 6,4x |
  | 20/set | US$ 25,6 mil | US$ 97 mil | 6,6x |
  | 27/set | US$ 27,4 mil | US$ 193 mil | 7,0x |
  | 4/out | US$ 34,1 mil | US$ 496 mil | 14,6x |
  | 11/out | US$ 54,6 mil | US$ 475 mil | 12,7x |
  | 14/out | US$ 67,3 mil | US$ 562 mil | 8,6x |

  A mediana nos dias com posição foi de 6,5x. O maior trade, um short de 4 BTC (US$ 336 mil) em 11/out, equivalia a ~6x o patrimônio sozinho.
- **O dia 8/out.** Ele virou de vendido para comprado em BTC, ETH e NEAR, e o mercado caiu. Saldo do dia: −US$ 15,8 mil (US$ 5,4 mil realizados e o resto de posição aberta). O recuo desde o pico foi de **−42%**. Ele manteve as posições, que se recuperaram em 3 dias (+US$ 20 mil de 9 a 11/out). O stop móvel limita cada trade, mas **não limita a soma** de várias posições grandes no mesmo lado.
- **Agora.** O patrimônio é de US$ 67 mil, quase todo parado em USDC. A única posição é um long de 10.000 PONS (US$ 3,3 mil, 3x), com stop em 0,30677. Os shorts de BTC e ETH foram fechados hoje.
- **Amostra.** São 7 semanas num único regime de mercado (alta das alts em setembro, lateral de BTC em outubro). Quatro dias (28/set, 7/out, 11/out e 13/out) somam +US$ 44,6 mil, 85% do PnL.

## 5. Dá para copiar?

Resultado de espelhar a posição real com atraso (marcação horária, sem custos):

| atraso | BTC | NEAR | ETH |
|---|---|---|---|
| 0h | +US$ 21,9 mil | +US$ 14,6 mil | +US$ 14,9 mil |
| 12h | +US$ 15,5 mil | +US$ 23,2 mil | +US$ 12,4 mil |
| 24h | +US$ 10,4 mil | +US$ 4,2 mil | +US$ 8,2 mil |
| 72h | +US$ 2,7 mil | −US$ 12,8 mil | +US$ 4,5 mil |

A vantagem está em um horizonte de **1 a 3 dias**. Com até 12h de atraso a cópia mantém quase tudo, e com 24h perde metade. Na prática, copiar exige alavancagem de 6–15x e seguir stops que mudam várias vezes por dia, e a API só mostra as ordens de gatilho abertas. O teste de regra do relatório automático (seção 10) não serve aqui: o período de treino é o bot de teste e o começo da conta, e a regra escolhida não opera.

## 6. O que esta carteira não é

- **Não é bot.** O agente "hermes-rail-live" só aparece no teste de 20–23/ago. As ordens de verdade são da interface e do app, em lotes redondos e com stops movidos à mão.
- **Não é hedge.** A subconta "Hedging" está vazia, não há staking nem saldo spot além de USDC, e as posições ficam ora líquido vendido, ora líquido comprado.
- **Não é market making.** 91% do nocional é *taker*.

## 7. Como monitorar

- **Se o bot voltar.** Ordens de ~US$ 11 ou um ritmo regular de minutos indicariam que o "hermes-rail-live" passou do teste para produção. A ordem pode até ser a mesma, mas aí a carteira deixa de ser manual.
- **Tamanho contra patrimônio.** O sinal de alerta é exposição bruta acima de 10x com várias posições no mesmo lado (como em 4/out e 8/out).
- Rodar `python -m hlre.run 0x0812f31ccf62c48e6da3da3fbf98663779e1f45d` e depois o `analise_extra.py`. O coletor faz merge do histórico (a API só guarda as últimas 2.000 ordens, e os stops são muitos).

## 8. Limitações

- **No relatório automático, a seção 6 de BTC e o perfil por ativo de BTC, ETH e SOL** estão dominados pelos ~1.000 trades de teste. Por exemplo, "389 ordens de BTC, tamanho mediano 0,00015" e o contexto "+17% em 72h" são da semana do teste, quando o BTC subiu 22%. O mesmo vale para os episódios de BTC e ETH (176 e 180, quase todos de segundos) e para o teste de replicação. O `analise_extra.py` separa as duas fases.
- **A exposição mensal do relatório automático** mostra equity perp de US$ 0 em agosto, porque a margem fica no spot (conta unificada). A alavancagem da seção 4 acima usa o patrimônio total.
- **Os stops antigos** só existem enquanto estiverem entre as últimas 2.000 ordens que a API guarda. Hoje cobrem 4/set em diante, o período inteiro da fase manual com stops.
- **Nada aqui é recomendação de investimento.**
