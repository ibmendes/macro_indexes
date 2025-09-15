# %%
### simples teste antes de alimentar o banco de dados 

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import Main

# cria instância do Main
main = Main(app_name="teste", host="localhost", port=5432, database="sgs_bacen")

spark = main.spark

# %%
import yfinance as yf
from datetime import date, timedelta
import pyspark.sql.functions as F


# yfinance https://ranaroussi.github.io/yfinance/
# yquery https://yahooquery.dpguthrie.com/
# yahoo finance https://finance.yahoo.com/
# %%
# teste da API

import yfinance as yf

tickers = ['VT', '^BVSP', '^GSPC', 'IDIV.SA', 'DIVO11.SA']

end = date.today()
start = '2022-01-03'

# baixa dados de 1 mês, corrigindo falhas (repair=True)
data = yf.download(
    tickers,
    start=start,
    end=end,
    repair=True
    )


# inclui a coluna 'Adj Close' (já ajustada por dividendos e splits)
print(data)

# %%
# transformar MultiIndex em formato longo
df = data.stack(level=1).reset_index()

# renomear colunas
df = df.rename(columns={
    "Date": "date",
    "level_1": "ticker"
})

print(df.head())

# %%
### spark fix

df_spark = spark.createDataFrame(df)

df_spark.show(10, truncate=False)
df_spark.printSchema()
print(df_spark.columns)

# %%

## final format 
df_spark = (
    df_spark
    .withColumn("High", F.round(df_spark["High"], 2))
    .withColumn("Low", F.round(df_spark["Low"], 2))
    .withColumn("Open", F.round(df_spark["Open"], 2))
    .withColumn("Close", F.round(df_spark["Close"], 2))
    .withColumn("Volume", F.round(df_spark["Volume"], 2))
    .withColumn("dataCotacao", F.to_date(F.col("date")))
    .withColumn("dt_ingestao",  F.current_timestamp())
    .withColumn(
        "tickerNome",
        F.when(F.col("Ticker") == "VT", F.lit("Vanguard Total World"))
        .when(F.col("Ticker") == "^BVSP", F.lit("Ibovespa"))
        .when(F.col("Ticker") == "^GSPC", F.lit("S&P 500"))
        .when(F.col("Ticker") == "IDIV.SA", F.lit("IDIV"))
        .otherwise(F.col("Ticker"))
    )
    .withColumn(
        "codigoTicker",
        F.when(F.col("Ticker") == "VT", F.lit("VT"))
        .when(F.col("Ticker") == "^BVSP", F.lit("IBOV"))
        .when(F.col("Ticker") == "^GSPC", F.lit("S&P500"))
        .when(F.col("Ticker") == "IDIV.SA", F.lit("IDIV"))
        .when(F.col("Ticker") == "DIVO11.SA", F.lit("IDIV - DIVO11 IT ETF"))
        .otherwise(F.col("Ticker"))
    )
    .select(
        F.col("dataCotacao"),
        F.col("Ticker").alias("ticker"),
        F.col("codigoTicker"),
        F.col("tickerNome"),
        F.col("Close").alias("fechamento"),
        F.col("High").alias("maiorAlta"),
        F.col("Open").alias("abertura"),
        F.col("Repaired?").alias("corrigiuDividendos"),
        F.col("Volume").alias("volume"),
        F.col("date").alias("dataHoraCotacao"),
        F.col("dt_ingestao")
    )
    .orderBy(F.col("dataCotacao").desc(), F.col("ticker")) \
)


df_spark.show(10, truncate=False)
df_spark.printSchema()

# %%
## Inserindo o primeiro batch historico 

df = df_spark
if df.count() > 0:
    main.write_df(df_spark, "cotacoes_indices", "raw", "append")

# %%
## teste def pipe 
from utils.stocks_indexes import get_indexes 

df = get_indexes(main.spark,main.connector)
df.show(5, truncate=False)
#%%
# main trigger
main.run()