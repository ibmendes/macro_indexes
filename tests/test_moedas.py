# %%
### simples teste antes de alimentar o banco de dados 

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import Main

# cria instância do Main
main = Main(app_name="teste", host="localhost", port=5432, database="sgs_bacen")

spark = main.spark

# from utils.sgs.moedas import get_moedas
# %%

from bcb import PTAX
import pandas as pd

ptax = PTAX()
ep = ptax.get_endpoint('CotacaoMoedaPeriodo')

moedas_fortes = ("USD", "EUR", "CHF")  # tupla ou lista de moedas
inicio = "01/01/2022"
fim = "01/05/2022"

dfs = []
for moeda in moedas_fortes:
    df = (ep.query()
            .parameters(moeda=moeda,
                        dataInicial=inicio,
                        dataFinalCotacao=fim)
            .collect())
    df["moeda"] = moeda
    dfs.append(df)

df = pd.concat(dfs)
print(df)

# %%
from pyspark.sql import DataFrame
import pyspark.sql.functions as F

df_spark = spark.createDataFrame(df)
df_spark = df_spark.filter(F.col("tipoBoletim") == "Fechamento") \
                    .withColumn("dataCotacao", F.to_date(F.col("dataHoraCotacao"))) \
                    .orderBy(F.col("dataCotacao").desc(), F.col("moeda").asc()) \
                    .select("dataCotacao", "moeda", "cotacaoCompra", "cotacaoVenda", 
               "paridadeCompra", "paridadeVenda", "dataHoraCotacao", "tipoBoletim")

df_spark.show(25,truncate=False)
df_spark.printSchema()

# %%
df = df_spark
if df.count() > 0:
    main.write_df(df, "cotacao_moedas", "raw", "append")

# %%

from utils.sgs.moedas import get_referencia

ref = get_referencia(main.connector)

print (ref)
# %%
from utils.sgs.moedas import get_cotacoes_moedas 
inicio = "01/01/2022"
fim = "01/05/2022"

df= get_cotacoes_moedas(main.spark, main.connector, inicio, fim)

df.show (10)

# %% 
from utils.sgs.moedas import get_boletins

df= get_boletins(inicio, fim)

print(df)
# %%

df_spark = main.spark.createDataFrame(df)
df_spark = df_spark.filter(F.col("tipoBoletim") == "Fechamento") \
                    .withColumn("dataCotacao", F.to_date(F.col("dataHoraCotacao"))) \
                    .withColumn("dt_ingestao",  F.current_timestamp()) \
                    .orderBy(F.col("dataCotacao").desc(), F.col("moeda").asc()) \
                    .select("dataCotacao", "moeda", "cotacaoCompra", "cotacaoVenda", 
            "paridadeCompra", "paridadeVenda", "dataHoraCotacao", "tipoBoletim","dt_ingestao") \

df_spark.show(5)      
# df_spark = df_spark.filter(F.col("datacotacao") > start_ref) \
#                     .dropDuplicates(["dataCotacao", "moeda"])

# %%
if df.count() > 0:
    main.write_df(df, "cotacao_moedas", "raw", "append")
# %%
# main trigger
main.run()
# %%
from bcb import PTAX

ptax = PTAX()
ep = ptax.get_endpoint("CotacaoMoedaPeriodo")

df = (
    ep.query()
    .parameters(
        moeda="USD",
        dataInicial="07/24/2026",
        dataFinalCotacao="09/29/2026"
    )
    .collect()
)

print(df)
# %%
from bcb import PTAX

ptax = PTAX()
ep = ptax.get_endpoint("CotacaoMoedaPeriodo")

query = (
    ep.query()
    .parameters(
        moeda="USD",
        dataInicial="07/24/2026",
        dataFinalCotacao="09/29/2026"
    )
)

print("URL:")
print(query.url)

print("\nRESPOSTA:")
response = query.text()

print("Tamanho:", len(response))
print(repr(response[:1000]))
# %%
import requests

url = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
)

params = {
    "@moeda": "'USD'",
    "@dataInicial": "'07-24-2026'",
    "@dataFinalCotacao": "'09-29-2026'",
    "$format": "json"
}

response = requests.get(url, params=params)

print("STATUS:", response.status_code)
print("URL:", response.url)
print("CONTENT-TYPE:", response.headers.get("content-type"))
print("TAMANHO:", len(response.text))
print("\nRESPOSTA:")
print(response.text[:2000])
# %%
