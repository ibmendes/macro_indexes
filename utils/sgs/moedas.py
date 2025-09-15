from bcb import PTAX
import pandas as pd
from datetime import date, timedelta


from pyspark.sql import DataFrame
import pyspark.sql.functions as F

def get_referencia(
    pg_conn,
    schema: str = "raw",
    tabela: str = "cotacao_moedas"
):
    """
    Retorna a data de referência mais recente no banco de dados.
    pg_conn = modulo de conexão ao banco (PostgresConnector / PostgresConnection)
    schema = schema do banco (default "raw")
    tabela = tabela onde buscar a data (default "cotacao_moedas")
    """
    conn = None
    try:
        conn = pg_conn.connect("sgs_bacen")
        cur = conn.cursor()
        cur.execute(f"SELECT MAX(datacotacao) FROM {schema}.{tabela};")
        max_data = cur.fetchone()[0]  # pode ser date ou None
        cur.close()
    except Exception:
        # Se ocorrer erro, devolve None
        max_data = None
    finally:
        if conn:
            conn.close()

    return max_data

def get_boletins(inicio:str, fim:str) -> pd.DataFrame:
    """
    filtra no endpoint da api as janelas moveis das moedas fortes
    """

    moedas_fortes = ("USD", "EUR", "CHF")
    ptax = PTAX()
    ep = ptax.get_endpoint('CotacaoMoedaPeriodo')
    
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

    return df

def get_cotacoes_moedas (
    spark,
    pg_conn,
    start: str = None, 
    end: str = None,
    schema: str = 'raw',
) -> DataFrame:
    """
    Parâmetros:
    - spark: SparkSession
    - pg_conn: Conector Postgres (para eventualmente usar get_referencia)
    - inicio (mm/dd/yyyy): data de inicio, se não preenchida irá atrás dos dados no banco de dados
    - fim (mm/dd/yyyy): se não preenchida, 10 anos, se inicio for vazia irá pegar hoje
    - schema: raw
    """

    # Se datas customizadas não forem passadas, define pelo histórico no Postgres
    if start is None:
        last_ref = get_referencia(pg_conn, schema=schema)
        if last_ref is not None:
            start_ref = last_ref.strftime("%m/%d/%Y")
        else:
            start_ref = (date.today() - timedelta(days=364*10)).strftime("%m/%d/%Y")
        end_ref = (date.today()- timedelta(days=1)).strftime("%m/%d/%Y")

        # ajusta para sexta-feira se cair no fim de semana, ptax não disponível retorna df vazio por algum motivo
        # data inicial
        end_ref_date = date.today() - timedelta(days=1)

        # ajusta para sexta-feira se cair no fim de semana
        if end_ref_date.weekday() == 5:  # sábado
            end_ref_date -= timedelta(days=1)
        elif end_ref_date.weekday() == 6:  # domingo
            end_ref_date -= timedelta(days=2)

        # formata para string
        end_ref = end_ref_date.strftime("%m/%d/%Y")

    else:
        # start customizado
        start_ref = start
        if end is None:
            # se end não fornecido, define 5 dias a partir do start
            start_date_obj = pd.to_datetime(start).date()
            end_ref = (start_date_obj + timedelta(days=5)).strftime("%m/%d/%Y")
        else:
            end_ref = end
        # no caso de janelas moveis quero trazer o primeiro dia (start) também, diferente do append acima
        last_ref = pd.to_datetime(start_ref).date() - timedelta(days=1)


    print(f"[INFO] Buscando cotações desde {pd.to_datetime(start_ref).strftime('%d/%m/%Y')} até {pd.to_datetime(end_ref).strftime('%d/%m/%Y')}...")

    df = get_boletins(start_ref, end_ref)
    df_spark = spark.createDataFrame(df)
    df_spark = df_spark.filter(F.col("tipoBoletim") == "Fechamento") \
                        .withColumn("dataCotacao", F.to_date(F.col("dataHoraCotacao"))) \
                        .withColumn("dt_ingestao",  F.current_timestamp()) \
                        .orderBy(F.col("dataCotacao").desc(), F.col("moeda").asc()) \
                        .select("dataCotacao", "moeda", "cotacaoCompra", "cotacaoVenda", 
                "paridadeCompra", "paridadeVenda", "dataHoraCotacao", "tipoBoletim","dt_ingestao") \
                
    df_spark = df_spark.filter(F.col("datacotacao") >  pd.to_datetime(start_ref).date()) \
                       .dropDuplicates(["dataCotacao", "moeda"])
                       
    return df_spark