import pandas as pd
from datetime import date, timedelta, datetime
from bcb import sgs
from pyspark.sql import DataFrame

def get_referencia(
    pg_conn,
    schema: str = "raw",
    tabela: str = "cdi"
):
    """
    Retorna a data de referência mais recente no banco de dados.
    pg_conn = modulo de conexão ao banco (PostgresConnector / PostgresConnection)
    schema = schema do banco (default "raw")
    tabela = tabela onde buscar a data (default "cdi")
    """
    conn = None
    try:
        conn = pg_conn.connect("sgs_bacen")
        cur = conn.cursor()
        cur.execute(f"SELECT MAX(data) FROM {schema}.{tabela};")
        max_data = cur.fetchone()[0]  # pode ser date ou None
        cur.close()
    except Exception:
        # Se ocorrer erro, devolve None
        max_data = None
    finally:
        if conn:
            conn.close()

    return max_data

def get_sgs_index (
    spark,
    pg_conn,
    code: int,
    nome_indice: str,
    schema: str = "raw",
    start: str = None,
    end: str = None
) -> DataFrame:
    """
    Consulta série temporal do SGS e retorna um DataFrame Spark estruturado.
    documentação api https://wilsonfreitas.github.io/python-bcb/
    OBS: !!! PARA INDICES MENSAIS COMEÇAR COM DIA 01-MM-AAAA
    Parâmetros:
    - spark: SparkSession
    - pg_conn: Conector Postgres (para eventualmente usar get_referencia)
    - code: código do SGS
    - nome_indice: nome do índice (ex: "euro_venda", "dolar_ptax", "igpm")
    - schema: raw
    - start (YYYY-MM-DD): data de inicio, se não preenchida irá atrás dos dados no banco de dados
    - end (YYYY-MM-DD): se não preenchida, 10 anos, se start for vazia irá pegar hoje
    """

    # Se datas customizadas não forem passadas, define pelo histórico no Postgres
    if start is None:
        # Sem start: usa referência no Postgres ou últimos 10 anos
        last_ref = get_referencia(pg_conn, schema=schema, tabela=nome_indice)
        if last_ref is not None:
            # d+1 para append
            print (f"[INFO] Ultima ingestão para o {code}({nome_indice}): {last_ref}")
            start_ref = last_ref
        else:
            # y-10
            start_ref = (date.today() - timedelta(days=364*10)).strftime("%Y-%m-%d")
        end_ref = (date.today()- timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        # start customizado
        start_ref = start
        if end is None:
            # se end não fornecido, define 10 anos a partir do start
            start_date_obj = pd.to_datetime(start).date()
            end_ref = (start_date_obj + timedelta(days=364*10)).strftime("%Y-%m-%d")
        else:
            end_ref = end
        # no caso de janelas moveis quero trazer o primeiro dia (start) também, diferente do append acima
        last_ref = pd.to_datetime(start_ref).date() - timedelta(days=1)

    print(f"[INFO] Buscando {nome_indice} (código {code}) do SGS desde {start_ref} até {end_ref}...")

    # Busca no SGS
    df = sgs.get(code, start=start_ref, end=end_ref)

    df = df.reset_index()
    df = df.rename(columns={
        "Date": "data",
        str(code): "valor"
    })


    # Estrutura final
    df["data"] = pd.to_datetime(df["data"]).dt.date
    df["valor"] = df["valor"].astype(float)
    df["cod_sgs"] = code
    df["nm_indice"] = nome_indice
    df["dt_ingestao"] = datetime.now()

    df = df[["cod_sgs", "nm_indice", "data", "valor", "dt_ingestao"]]

    df_spark = spark.createDataFrame(df)
    df_spark = df_spark.filter(df_spark["data"] > start_ref)
    df_spark = df_spark.orderBy(df_spark["data"].desc())
    df_spark = df_spark.dropDuplicates(["cod_sgs", "data"])
    return df_spark