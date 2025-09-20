from utils.connect import *
from utils.sgs import *
from utils.stocks_indexes import *

from pyspark.conf import SparkConf
from pyspark.sql import SparkSession
from utils.connect import *

import logging 
import subprocess
import os

class Main:
    """
    Classe central para inicializar Spark e fornecer JDBC URL para Postgres.
    """

    def __init__(self, app_name="BacenETL", host="postgres", port=5432, database="sgs_bacen"):
        """
        Inicializa Spark com configuração local otimizada e conexão Postgres.
        """
        # Configura logger dentro da classe
        self.BacenMainLogger = logging.getLogger("BacenMainLogger")
        self.BacenMainLogger.setLevel(logging.INFO)

        if not self.BacenMainLogger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s [%(name)s] [%(levelname)s] - %(message)s"
            )
            handler.setFormatter(formatter)
            self.BacenMainLogger.addHandler(handler)

        self.BacenMainLogger.info("Inicializando sessão Spark...")

        self.spark = SparkSession.builder \
            .appName(app_name) \
            .master("local[*]") \
            .config(conf=SparkConf()
                    .set("spark.sql.shuffle.partitions", "4")
                    .set("spark.driver.memory", "2g")
                    .set("spark.executor.memory", "2g")
                    .set("spark.ui.port", "4040")
                    .set("spark.ui.enabled", "true")
                    .set("spark.sql.adaptive.enabled", "true")
                    ).enableHiveSupport().getOrCreate()

        self.BacenMainLogger.info("Sessão Spark inicializada ✅")
        # Conector Postgres
        self.connector = PostgresConnection(host=host, port=port)
        self.BacenMainLogger.info("Conexão postgres inicializada ✅")
        self.BacenMainLogger.info(f"({host} {port})")
        self.database = database

    def jdbc_url(self, schema=None):
        schema = schema or "public"
        return self.connector.jdbc_url(database=self.database, schema=schema)

    def write_df(self, df, table_name, schema=None, mode="overwrite", user="postgres", password="postgres"):
        schema = schema or "public"
        self.BacenMainLogger.info(f"Escrevendo DataFrame em {schema}.{table_name}...")

        df.write \
            .format("jdbc") \
            .option("url", self.jdbc_url(schema=schema)) \
            .option("dbtable", f"{schema}.{table_name}") \
            .option("user", self.connector.user) \
            .option("password", self.connector.password) \
            .option("driver", "org.postgresql.Driver") \
            .mode(mode) \
            .save()

        self.BacenMainLogger.info(f"DataFrame salvo em {schema}.{table_name} ✅")
    
    def run_dbt_model(self, model_name: str):
        # Caminho absoluto para o diretório do projeto dbt
        modelo_dbt= os.path.join(os.path.dirname(__file__), "dbt_macro_modelling")

        command = f"dbt run -m {model_name} --project-dir {modelo_dbt} --profiles-dir {modelo_dbt}"

        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )

        for line in process.stdout:
            print(line, end="")

        process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"Erro ao executar o modelo dbt: {model_name}")
    
    def run(self):
        """
        Executa o pipeline de ETL.
        cada script em sua def final gera um df, que aqui é escrito no Postgres.
        """
        
        #################### camada raw ###########################
        #ipca
        self.BacenMainLogger.info("iniciando ipca")
        df = get_sgs_index(self.spark,self.connector,433,'ipca',"raw")
        if df.count() > 0:
            self.write_df(df, "ipca", "raw", "append")
        #cdi
        self.BacenMainLogger.info("iniciando cdi")
        df = get_sgs_index(self.spark,self.connector,12,'cdi',"raw")
        if df.count() > 0:
            self.write_df(df, "cdi", "raw", "append")
        #igpm
        self.BacenMainLogger.info("iniciando igpm")
        df = get_sgs_index(self.spark,self.connector,189,'igpm',"raw")
        if df.count() > 0:
            self.write_df(df, "igpm", "raw", "append")

        # moedas 
        self.BacenMainLogger.info("iniciando moedas")
        df = get_cotacoes_moedas(self.spark,self.connector)
        if df.count() > 0:
            self.write_df(df, "cotacao_moedas", "raw", "append")

        self.BacenMainLogger.info("iniciando indices")
        df = get_indexes(self.spark,self.connector)
        if df.count() > 0:
            self.write_df(df, "cotacoes_indices", "raw", "append")
        ##########################################################
        #               fim camada bronze                        #   
        ##########################################################
        # Rodar o modelo silver
        self.BacenMainLogger.info("🔹 Rodando modelo silver: variacao_indices")
        self.run_dbt_model("variacao_indices")
        
        # # Rodar o modelo gold
        self.BacenMainLogger.info("🔹 Rodando modelo gold: retorno_indices")
        self.run_dbt_model("retorno_indices")

        self.BacenMainLogger.info("Pipeline ETL finalizado ✅")
        

if __name__ == "__main__":
    main = Main()
    main.BacenMainLogger.info("Iniciando pipeline...")
    main.run()
