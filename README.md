# Hyperliquid RE: engenharia reversa de carteiras lucrativas

Ferramentas e relatórios para entender **o que** carteiras lucrativas da Hyperliquid fazem, **como** executam, **de onde** vem o lucro e **se** dá para replicar ou copiar.

Tudo é feito com dados públicos: a API `POST https://api.hyperliquid.xyz/info` (não precisa de chave) e, para preços horários antigos, o arquivo público de klines da Binance.

## Carteiras analisadas

| carteira | veredito curto | análise |
|---|---|---|
| `0xcac1f1c3e4599e044dc2a9d38a9b6ef1af1bdae8` | Trader **discricionário manual**, viés **vendido** concentrado em BTC perp; vende força, carrega a tendência. Lucro concentrado num short de 158 dias (out/2025 → mar/2026, +US$ 3,07M), mais US$ 1,03M de funding. Alavancagem de 5–17x, sem stop, uma liquidação de US$ 4,2M. O short de HYPE é hedge de ~91k HYPE em staking em carteiras ligadas. | [ANALISE.md](reports/0xcac1f1c3e4599e044dc2a9d38a9b6ef1af1bdae8/ANALISE.md) · [relatório automático](reports/0xcac1f1c3e4599e044dc2a9d38a9b6ef1af1bdae8/relatorio_auto.md) |
| `0xfce053a5e461683454bf37ad66d20344c0e3f4c0` | Trader **manual (app de celular)** e **só vendido**, com dois livros: (1) short de memecoins com compradores lotados (funding alto, moeda já fora do topo), segurado por semanas, +US$ 3,4M; (2) short macro de BTC/ETH a partir do topo de out/2025, aumentado depois da quebra de nov/2025 (até US$ 27M), +US$ 6,3M. Sem stop; margem trazida de fora quando precisa e lucro sacado em seguida. US$ 10,8M em 22 meses, mas −US$ 1,06M nos últimos 4 meses. O padrão das alts tem vantagem no universo inteiro da Hyperliquid; o macro não vira regra. | [ANALISE.md](reports/0xfce053a5e461683454bf37ad66d20344c0e3f4c0/ANALISE.md) · [relatório automático](reports/0xfce053a5e461683454bf37ad66d20344c0e3f4c0/relatorio_auto.md) |
| `0x16bf84af3f85f8c8a97597bf2be549dfe0dee637` | **Swing trader manual de BTC nos dois lados**, contra o movimento curto: vende repiques no topo do range de 7 dias e compra quedas no fundo, entra com escadas de limites (ordem *Scale* da interface) e sai com blocos agressivos de 50–250 BTC. Longs de prazo maior ficam no **spot UBTC** (sem funding nem liquidação), trocados com o perp no mesmo minuto. Aporte único de 27 BTC (US$ 3,0M) em out/2025 → US$ 9,09M, +US$ 6,09M em 12 meses, sem saques. Extras: prata HIP-3 depois do crash (+US$ 1,54M) e um short de ZEC parabólico (−US$ 0,58M). Alavancagem de 1–3x, sem stop. A regra mecânica equivalente não tem vantagem. | [ANALISE.md](reports/0x16bf84af3f85f8c8a97597bf2be549dfe0dee637/ANALISE.md) · [relatório automático](reports/0x16bf84af3f85f8c8a97597bf2be549dfe0dee637/relatorio_auto.md) |
| `0x0748e296e5a350ec36c8487a1cea406e1b57d4b2` | **Long/short discricionário de altcoins por fundamentos**: comprado em tokens com receita ou recompra (AAVE, UNI, LDO, PENDLE, JUP, HYPE, PUMP, ZEC), vendido em L1s sem receita e lançamentos de VC com desbloqueio (ADA, XLM, XRP, SUI, AVAX, IP, WLD, WLFI). Exposição bruta de 1–2x, execução manual com TWAP nativo e *chase*. +US$ 12,4M em 28 meses a partir de ~US$ 100k (perps +US$ 7,3M, PUMP spot e HYPE o resto), US$ 7,1M sacados. O livro long é beta; o alfa está no short (lançamentos de VC) e em reagir dentro do dia (~US$ 5,2M dos US$ 8,2M de preço). A cesta da tese, fora da amostra, dá +71% a.a. long−short, com IC que encosta no zero. | [ANALISE.md](reports/0x0748e296e5a350ec36c8487a1cea406e1b57d4b2/ANALISE.md) · [relatório automático](reports/0x0748e296e5a350ec36c8487a1cea406e1b57d4b2/relatorio_auto.md) |
| `0x8bae3527e5a33fa0cf184f37bc112d071463ab6d` | **Não é estratégia de mercado: transferência de valor em livros ilíquidos.** São 50 "eventos" em 30 altcoins pouco negociadas (GAS, NEO, CELO, IOTA, FTT, RSR, kNEIRO, BSV…). Em cada um, a carteira compra US$ 1–2M **~10% abaixo do preço justo**, num preço que **nunca existiu na Binance**. Em 2025 a ordem limite dela é atingida por um vendedor **0,1–0,5 s depois** de entrar no livro; em 2026 ela compra uma venda barata que já está à espera. Desconto embutido: US$ 7,6M. Total de +US$ 12,0M em 15 meses sobre US$ 0,5M depositados. A carteira que a indicou (`0x9458…ec04`, código com um único indicado) fez o mesmo de fev a nov/2025 (+US$ 11,1M) e passou o dinheiro para esta no mesmo dia. Ao lado disso há um livro legítimo de ações HIP-3 (+US$ 2,4M, Intel +1,4M). A hipótese mais provável é dreno de contas de terceiros (chaves de API vazadas); confirmar pelos hashes dos fills. Não copiável. | [ANALISE.md](reports/0x8bae3527e5a33fa0cf184f37bc112d071463ab6d/ANALISE.md) · [relatório automático](reports/0x8bae3527e5a33fa0cf184f37bc112d071463ab6d/relatorio_auto.md) |
| `0xd260b2216b735277da6771564a01c04856e78321` | **Trader manual de grande porte, comprado e sem stop**: compra quedas em BTC, HYPE, SOL e ETH com US$ 5–56M de nocional, realiza nos repiques em dias, aumenta contra o preço e traz margem de fora (US$ 61M depositados e US$ 22,6M de uma hot wallet de exchange). +US$ 8,55M em 20 meses, quase tudo **HYPE** (perp +US$ 5,4M, spot e staking ~+US$ 3,6–5,3M), num período em que o HYPE foi de US$ 25 a 90, e mais beta do que timing. BTC perdeu ~US$ 6,5M; um long de 888 BTC em jun/2026 (−US$ 5,8M) zerou o lucro acumulado. O staking de HYPE segue as faixas de desconto de taxa (1k/10k/100k); o caixa parado vai para o HLP ou para o *lending* de USDC. Liquidado a 42x no crash de 10/out/2025. Não copiável. | [ANALISE.md](reports/0xd260b2216b735277da6771564a01c04856e78321/ANALISE.md) · [relatório automático](reports/0xd260b2216b735277da6771564a01c04856e78321/relatorio_auto.md) |
| `0x833b99b27dac651d02080f5e220e929df891db06` | **Carry de funding em BTC, provavelmente com hedge fora da Hyperliquid**: fica vendido no perp em 74% dos dias, com o tamanho dado pelo funding da semana anterior (zerado com funding ≤ 0, ~100 BTC acima de 15% a.a.; correlação −0,51). Execução manual, *post-only* (98% *maker* em BTC, 0,73 bp), lotes de 1–5 BTC. Mantém pouca margem (mediana de US$ 0,57M para shorts de até US$ 20M, 8–40x) e saca o lucro e repõe o prejuízo quase todo dia (fluxo × PnL: −0,85 em 30 dias), o padrão de um basis trade. +US$ 7,78M em 17 meses, mas US$ 4,95M são preço do BTC numa queda de 115k para 60k; funding +US$ 0,86M e livro de HIP-3 (S&P 500 com funding negativo) ~+US$ 1,6M. Sem hedge, a mesma regra perderia US$ 4,3M em 2023–25. Nada direcional para copiar. | [ANALISE.md](reports/0x833b99b27dac651d02080f5e220e929df891db06/ANALISE.md) · [relatório automático](reports/0x833b99b27dac651d02080f5e220e929df891db06/relatorio_auto.md) |
| `0x78dce96236804d6958bf3c4598cf5efbc371629c` | **Bot de market making HFT em BTC perp**, subconta "kakaroto" de uma firma com 50 subcontas (mestre `0x7839…9916`, ~US$ 400M/dia, ~7% do volume da bolsa). Só *post-only* com `cloid`, ~30 ordens/s, 0% *taker*, rebate de −0,3 bp. +US$ 252k em 14,5 meses com US$ 4,76B de volume e US$ 12–45k de margem (0,53 bp do volume). Neutro até jul/2026 (+0,73 bp); desde ago/2026 carrega um short fixo de 6–13 BTC a 17–37x, que perdeu US$ 119k em agosto (−1,18 bp nos últimos 30 dias). O grupo inteiro está vendido em ~23 BTC; se é hedge, é fora da Hyperliquid. Não copiável. | [ANALISE.md](reports/0x78dce96236804d6958bf3c4598cf5efbc371629c/ANALISE.md) · [relatório automático](reports/0x78dce96236804d6958bf3c4598cf5efbc371629c/relatorio_auto.md) |
| `0xc7c37b0c7af5af560bf31b0bcbfec04b97361275` | **Trader manual pequeno** (US$ 4 mil depositados em jul/2026, US$ 22 mil de PnL em 3 meses) que faz **trades de par neutros em dólar**: BTC contra ouro (HIP-3), ouro contra BTC e ETH contra BTC, executados com duas TWAPs simultâneas. 4 de 5 pares com lucro, mas a amostra é pequena e a regra de entrada muda (tendência nos pares BTC/ouro, reversão nos últimos). O tamanho cresceu a cada ganho: o par aberto tem US$ 250 mil por perna, 25x o patrimônio. | [ANALISE.md](reports/0xc7c37b0c7af5af560bf31b0bcbfec04b97361275/ANALISE.md) · [relatório automático](reports/0xc7c37b0c7af5af560bf31b0bcbfec04b97361275/relatorio_auto.md) |
| `0x0812f31ccf62c48e6da3da3fbf98663779e1f45d` | **Trader manual de conta pequena que escalou rápido**: US$ 18,7 mil depositados viraram US$ 67 mil em 7 semanas (+US$ 52,4 mil). Vende alts depois de alta forte (+41% em 30 dias na mediana: NEAR, LTC, ARB, FARTCOIN, UNI, ZEC), +US$ 19 mil, e faz swing de BTC/ETH nos dois lados (+US$ 32 mil). Usa **stop móvel à mão** (413 ordens de gatilho, ~4 por dia por moeda); ganho médio 2,9x a perda média. O tamanho cresceu de US$ 15 mil para US$ 336 mil por trade (até 14,6x o patrimônio) e um dia ruim (8/out) levou 42% do patrimônio do pico. Antes disso, um agente de API "hermes-rail-live" fez ~1.000 trades de teste de US$ 11 em BTC/ETH/SOL (20–23/ago). Amostra curta demais para virar regra. | [ANALISE.md](reports/0x0812f31ccf62c48e6da3da3fbf98663779e1f45d/ANALISE.md) · [relatório automático](reports/0x0812f31ccf62c48e6da3da3fbf98663779e1f45d/relatorio_auto.md) |
| `0xa5fd942d4badbab4fe84a9e10f565dd40d5f15ff` | **Trader manual de escadas de ordens limite num livro largo de alts, comprado e sem stop**: coloca de uma vez 7–97 limites do mesmo tamanho (ordem *Scale* da interface) 10–40% longe do preço e deixa por semanas (555 ordens abertas hoje, US$ 3,9M de compra e US$ 4,0M de venda); compra recuos de alts em alta e vende cada lote numa limite acima. US$ 235 mil depositados em dez/2024 viraram US$ 2,52M (+US$ 2,21M em perps em 22 meses). No período com fills (mai–out/2026), alts +US$ 935 mil (LIT +261 mil, MET +257 mil, HYPE +140 mil), BTC/ETH −US$ 78 mil; lotes limite→limite +US$ 764 mil. O lucro está no caminho do preço dentro do dia: a posição média diária explica só US$ 98 mil do US$ 1,31M anterior aos fills. Recuo de −54% em 2025 (short de IP no squeeze), 16 liquidações em margem isolada (−US$ 128 mil), −US$ 236 mil de funding. A escada mecânica no universo inteiro acerta 51–82% mas tem média ~0: a vantagem é a escolha das moedas. Não copiável como regra. | [ANALISE.md](reports/0xa5fd942d4badbab4fe84a9e10f565dd40d5f15ff/ANALISE.md) · [relatório automático](reports/0xa5fd942d4badbab4fe84a9e10f565dd40d5f15ff/relatorio_auto.md) |
| `0x63d417a577b50c96f4f09148d4e4d70950db0522` | **Trader manual alavancado de altcoins, com livro líquido comprado de US$ 2,9M hoje.** +US$ 3,29M all-time (perps +US$ 3,10M), mas 13 liquidações próprias nos fills somam −US$ 383k, sobretudo LIT (−US$ 237k). A direção líquida muda de mês para mês. O PnL antes de 08/jul/2026 é estimado; o maior bloco estimado é um short de MERL (+US$ 1,7M), sem regra replicável. A cópia com 30 min de atraso fica com 82% na janela de 3 meses, mas o simulador ignora margem e liquidação. Não copiável como regra. | [ANALISE.md](reports/0x63d417a577b50c96f4f09148d4e4d70950db0522/ANALISE.md) · [relatório automático](reports/0x63d417a577b50c96f4f09148d4e4d70950db0522/relatorio_auto.md) |

## Como usar

```bash
pip install -r requirements.txt

# pipeline completo: baixa dados da carteira e de mercado, gera o relatório
# (se a carteira for copiável, baixa também os candles de 15m/1h usados na simulação de cópia)
python -m hlre.run 0xENDERECO

# ou etapa por etapa
python -m hlre.collect 0xENDERECO                    # fills, funding, ledger, ordens, snapshot, carteiras ligadas
python -m hlre.market BTC HYPE --intervals 1h 4h 1d  # candles + histórico de funding (Hyperliquid)
python -m hlre.market LIT MET --intervals 1h 15m --no-funding  # preços intradiários para a cópia com atraso
python -m hlre.binance BTCUSDT --start 2025-01       # 1h antigos (arquivo público Binance)
python -m hlre.report 0xENDERECO --coins BTC HYPE    # gera reports/<carteira>/relatorio_auto.md

# testes de regras no universo inteiro de perps (para validar um padrão de entrada)
python -m hlre.universe fetch                        # candles diários de todos os perps, inclusive deslistados
python -m hlre.universe study --start 2024-12-16 --funding-a POPCAT TRUMP --funding-b APT WIF
                                                     # gera reports/estudos/regras_short.md
```

Saída em `reports/<carteira>/`:

- `relatorio_auto.md`: números, tabelas e gráficos gerados automaticamente;
- `img/*.png`: os gráficos;
- `metrics.json`: os números principais, para comparar carteiras;
- `ANALISE.md`: a interpretação da estratégia, escrita à mão a partir do relatório;
- `analise_extra.py` (quando existe): recalcula os números do `ANALISE.md` que não estão no relatório automático.

**Rode o coletor periodicamente.** A API só serve os fills mais recentes (aqui, os de mai/2025 em diante) e as últimas 2.000 ordens. O coletor faz merge com o que já existe em `data/`, então o histórico local cresce a cada execução.

## Método

| pergunta | como é respondida |
|---|---|
| Quanto ganhou e quando? | `portfolio` (curvas de PnL e equity all-time, perp e total) |
| Em que ativos, com que tamanho? | posição exata a partir dos fills (`startPosition` + tamanho); **antes dos fills**, a posição diária vem do histórico de **funding**, que traz o tamanho da posição (`szi`) desde a abertura da conta |
| De onde vem o PnL? | marcação diária exata (posição carregada × movimento + fills marcados no fechamento), dividida em viés, timing do tamanho, trades intradiários, funding e taxas |
| Bot, market maker ou manual? | `historicalOrders` (tipo e TIF: `FrontendMarket` = interface web), `extraAgents` (API wallets), % maker/taker, tamanhos de lote, ritmo das sessões |
| O que dispara entradas e saídas? | contexto de mercado em cada ordem (retornos de 1h a 7d, posição no range de 7d, retorno futuro) vs. a base de todas as horas, com teste de Mann-Whitney por sessão |
| Como gere risco? | aumentos com a posição no prejuízo (preço médio), taxa de acerto das reduções, alavancagem (exposição / equity), ordens de gatilho, liquidações e ADL |
| É hedge de algo? | carteiras ligadas: conta de staking vinculada para desconto de taxa, contrapartes de transferências, airdrops idênticos |
| Dá para replicar com regras? | busca em grade de regras (tendência + fade do range) com treino e teste separados, mais um clone por regressão; compara a correlação com a posição real e o PnL |
| Dá para copiar? | primeiro, um teste de copiabilidade: há execuções de perps suficientes, menos da metade do volume fecha em menos de 30 min (tempo em posição por LIFO) e não é bot de market making (≥ 300 execuções por dia ativo e ≥ 80% maker). Se passar, simula um copiador que repete cada fill com **30 min, 1h, 2h e 4h** de atraso, no mesmo tamanho, a mercado e com taxa *taker*: PnL da cópia contra o da carteira nas mesmas operações, quanto fica, custo em bp do volume com IC 95%, drawdown, por ativo e por tipo de execução. Também mostra o PnL de espelhar a posição com 0 a 168h de atraso |
| Cada trade, por dentro | episódios de zerado a zerado em todas as moedas: contexto antes da 1ª ordem (retornos, distância da máxima de 30 dias, funding), preço médio vs. 1ª ordem, excursão contra, pior PnL aberto, quanto capturou |
| Como usa o dinheiro? | depósitos e saques contra o PnL dos dias anteriores e contra a variação da exposição (margem sob demanda) |
| É long/short de cestas? | posição diária em US$ por moeda (funding), livro long × livro short, beta ao BTC e alfa com bootstrap, comparação com cestas fixas e teste fora da amostra (`analise_extra.py` da `0x0748`) |
| O padrão vale fora das moedas que ele escolheu? | `hlre.universe`: estudo de eventos em todos os perps (inclusive deslistados) contra a base de "shortar qualquer alt", funding por faixas numa amostra aleatória, regras de média móvel em BTC/ETH desde 2020; intervalos por bootstrap de semanas |

## Estrutura

```
hlre/
  api.py        cliente da Info API (throttle, retry, paginação por tempo)
  collect.py    download e merge incremental dos dados da carteira + carteiras ligadas
  market.py     candles e histórico de funding da Hyperliquid; série horária costurada
  binance.py    klines horários do arquivo público da Binance (contexto antigo)
  analyze.py    execuções, episódios, posições, PnL exato e aproximado, contexto, teste de copiabilidade e cópia com atraso
  replicate.py  backtest diário, regras replicantes, clone comportamental
  universe.py   testes de regras no universo inteiro de perps (eventos, funding, médias móveis)
  charts.py     gráficos estáticos (sem eixo duplo; azul = long/ganho, vermelho = short/perda)
  report.py     relatório automático em markdown
  run.py        pipeline completo
data/           dados brutos (json.gz/csv.gz) de carteiras e de mercado
reports/        relatórios por carteira; reports/estudos/ guarda os testes de universo
```

## Limitações

- Quando os fills cobrem todo o histórico (carteiras com menos de ~10 mil fills), o PnL diário é exato e bate com o `portfolio`; o relatório avisa quando é o caso.
- O PnL por ativo **antes** do período com fills é aproximado (posição média diária × movimento do dia) e não captura day trade. No período com fills, a correlação diária com o valor exato foi 0,95.
- Fatias de **TWAP** não aparecem em `userFills` e o endpoint delas só guarda as 2.000 mais recentes. O `Wallet` junta as que existem e `position_gaps` aponta saltos de posição sem fill. Quando há saltos, o relatório avisa e o PnL "exato" deixa de ser exato.
- Intenção (aposta ou hedge) é inferência: a API não mostra CEXs nem outras chains.
- **Cópia com atraso.** O preço da cópia é a abertura do candle que começa mais perto de *fill + atraso*. São candles de 15m da Hyperliquid nos últimos ~52 dias e de 1h da Hyperliquid (~7 meses) ou da Binance antes disso, então o atraso real varia meio candle para cada lado. Moedas só da Hyperliquid (e HIP-3) com fills mais antigos que os candles de 1h ficam sem preço; o relatório diz quanto do volume ficou de fora. O copiador começa zerado no primeiro fill do `userFills`, não copia posições já abertas e opera no mesmo tamanho (sem impacto de mercado). O funding fica de fora. Saltos de posição sem fill (TWAP) entram como execuções sintéticas iguais para os dois lados.
- Nada aqui é recomendação de investimento.
