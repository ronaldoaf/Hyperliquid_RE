# Hyperliquid RE: engenharia reversa de carteiras lucrativas

Ferramentas e relatórios para entender **o que** carteiras lucrativas da Hyperliquid fazem, **como** executam, **de onde** vem o lucro e **se** dá para replicar ou copiar.

Tudo é feito com dados públicos: a API `POST https://api.hyperliquid.xyz/info` (não precisa de chave) e, para preços horários antigos, o arquivo público de klines da Binance.

## Carteiras analisadas

| carteira | veredito curto | análise |
|---|---|---|
| `0xcac1f1c3e4599e044dc2a9d38a9b6ef1af1bdae8` | Trader **discricionário manual**, viés **vendido** concentrado em BTC perp; vende força, carrega a tendência. Lucro concentrado num short de 158 dias (out/2025 → mar/2026, +US$ 3,07M), mais US$ 1,03M de funding. Alavancagem de 5–17x, sem stop, uma liquidação de US$ 4,2M. O short de HYPE é hedge de ~91k HYPE em staking em carteiras ligadas. | [ANALISE.md](reports/0xcac1f1c3e4599e044dc2a9d38a9b6ef1af1bdae8/ANALISE.md) · [relatório automático](reports/0xcac1f1c3e4599e044dc2a9d38a9b6ef1af1bdae8/relatorio_auto.md) |

## Como usar

```bash
pip install -r requirements.txt

# pipeline completo: baixa dados da carteira e de mercado, gera o relatório
python -m hlre.run 0xENDERECO

# ou etapa por etapa
python -m hlre.collect 0xENDERECO                    # fills, funding, ledger, ordens, snapshot, carteiras ligadas
python -m hlre.market BTC HYPE --intervals 1h 4h 1d  # candles + histórico de funding (Hyperliquid)
python -m hlre.binance BTCUSDT --start 2025-01       # 1h antigos (arquivo público Binance)
python -m hlre.report 0xENDERECO --coins BTC HYPE    # gera reports/<carteira>/relatorio_auto.md
```

Saída em `reports/<carteira>/`:

- `relatorio_auto.md`: números, tabelas e gráficos gerados automaticamente;
- `img/*.png`: os gráficos;
- `metrics.json`: os números principais, para comparar carteiras;
- `ANALISE.md`: a interpretação da estratégia, escrita à mão a partir do relatório.

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
| Dá para copiar? | PnL de espelhar a posição com 0 a 168h de atraso |

## Estrutura

```
hlre/
  api.py        cliente da Info API (throttle, retry, paginação por tempo)
  collect.py    download e merge incremental dos dados da carteira + carteiras ligadas
  market.py     candles e histórico de funding da Hyperliquid; série horária costurada
  binance.py    klines horários do arquivo público da Binance (contexto antigo)
  analyze.py    execuções, episódios, posições, PnL exato e aproximado, contexto, cópia com atraso
  replicate.py  backtest diário, regras replicantes, clone comportamental
  charts.py     gráficos estáticos (sem eixo duplo; azul = long/ganho, vermelho = short/perda)
  report.py     relatório automático em markdown
  run.py        pipeline completo
data/           dados brutos (json.gz/csv.gz) de carteiras e de mercado
reports/        relatórios por carteira
```

## Limitações

- O PnL por ativo **antes** do período com fills é aproximado (posição média diária × movimento do dia) e não captura day trade. No período com fills, a correlação diária com o valor exato foi 0,95.
- Intenção (aposta ou hedge) é inferência: a API não mostra CEXs nem outras chains.
- Nada aqui é recomendação de investimento.
