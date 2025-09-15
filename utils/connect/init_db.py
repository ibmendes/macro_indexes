# query_n 
## cria as tabelas if not exists para a camada raw

from .postgres import PostgresConnection

pg = PostgresConnection()
conn = pg.connect("sgs_bacen")  # conecta no DB
cur = conn.cursor()

# schema
cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
conn.commit()  # não esqueça de aplicar a alteração no banco


#### n queries para parses 

ipca = """
CREATE TABLE IF NOT EXISTS raw.ipca (
    cod_sgs BIGINT NOT NULL,
    nm_indice VARCHAR(50) NOT NULL,
    data DATE NOT NULL,
    valor DOUBLE PRECISION,
    dt_ingestao TIMESTAMP,
    PRIMARY KEY (cod_sgs, data)
);
"""

cdi = """
CREATE TABLE IF NOT EXISTS raw.cdi (
    cod_sgs BIGINT NOT NULL,
    nm_indice VARCHAR(50) NOT NULL,
    data DATE NOT NULL,
    valor DOUBLE PRECISION,
    dt_ingestao TIMESTAMP,
    PRIMARY KEY (cod_sgs, data)
);
"""

igpm = """
CREATE TABLE IF NOT EXISTS raw.igpm (
    cod_sgs BIGINT NOT NULL,
    nm_indice VARCHAR(50) NOT NULL,
    data DATE NOT NULL,
    valor DOUBLE PRECISION,
    dt_ingestao TIMESTAMP,
    PRIMARY KEY (cod_sgs, data)
);
"""

### moedas
moedas = """
CREATE TABLE IF NOT EXISTS raw.cotacao_moedas (
    dataCotacao     DATE NOT NULL,
    moeda           VARCHAR(10) NOT NULL,
    cotacaoCompra   DOUBLE PRECISION,
    cotacaoVenda    DOUBLE PRECISION,
    paridadeCompra  DOUBLE PRECISION,
    paridadeVenda   DOUBLE PRECISION,
    dataHoraCotacao TIMESTAMP,
    tipoBoletim     VARCHAR(20),
    dt_ingestao     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (dataCotacao, moeda)
);
"""

indices = """
CREATE TABLE IF NOT EXISTS raw.cotacoes_indices (
    dataCotacao DATE,
    ticker VARCHAR(20),
    codigoTicker VARCHAR(20),
    tickerNome VARCHAR(100),
    fechamento DOUBLE PRECISION,
    maiorAlta DOUBLE PRECISION,
    abertura DOUBLE PRECISION,
    corrigiuDividendos BOOLEAN,
    volume DOUBLE PRECISION,
    dataHoraCotacao TIMESTAMP,
    dt_ingestao TIMESTAMP NOT NULL,
    PRIMARY KEY (dataCotacao, codigoTicker)
);
"""
# cria a tabela se não existir
pg.create_table(ipca, schema="raw", table_name="ipca")
pg.create_table(cdi, schema="raw", table_name="cdi")
pg.create_table(igpm, schema="raw", table_name="igpm")
pg.create_table(moedas, schema="raw", table_name="cotacao_moedas")
pg.create_table(indices, schema="raw", table_name="cotacoes_indices")
