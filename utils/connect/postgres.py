import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

class PostgresConnection:
    def __init__(self, host=None, port=None, user=None, password=None):
        """
        Inicializa a conexão com o PostgreSQL.
        Valores padrão vêm do Docker/env, mas podem ser sobrescritos.
        """
        self.host = host or os.getenv("POSTGRES_HOST", "postgres")
        self.port = port or int(os.getenv("POSTGRES_PORT", 5432))
        self.user = user or os.getenv("POSTGRES_USER", "hiveuser")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "hivepassword")

    def connect(self, database="postgres"):
        """Conecta ao PostgreSQL; tenta localhost se falhar no host principal."""
        try:
            return psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=database
            )
        except Exception as e:
            print(f"[WARN] Falha ao conectar em {self.host}:{self.port} → {e}")
            print("[INFO] Tentando conectar via localhost...")
            self.host = "localhost"  # atualiza o host
            return psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=database
            )
        
    def create_database_if_not_exists(self, dbname="sgs_bacen"):
        """Cria o banco se não existir e define owner."""
        conn = self.connect("postgres")
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (dbname,))
        exists = cur.fetchone()

        if not exists:
            cur.execute(f'CREATE DATABASE "{dbname}" OWNER "{self.user}";')
            print(f"[OK] Banco {dbname} criado com sucesso com owner {self.user}!")

        cur.close()
        conn.close()

    def create_table(self, create_table_query, schema:str = None, table_name=None, database="sgs_bacen", owner=None):
        """
        Cria uma tabela a partir de uma query SQL.
        Define owner se table_name for passado, somente se a tabela for criada.
        """
        owner = owner or self.user
        schema = schema or "public"
        conn = self.connect(database)
        cur = conn.cursor()

        table_created = False

        try:
            if table_name:
                # verifica se a tabela já existe no schema especificado
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = %s
                        AND table_name = %s
                    );
                """, (schema, table_name))
                exists = cur.fetchone()[0]
            else:
                exists = False

            if not exists:
                cur.execute(create_table_query)
                table_created = True  # flag
                print(f"[INFO] Tabela {table_name} criada com sucesso")
            else:
                print(f"[INFO] Tabela {table_name} já existe, pulando criação")

            # onwer apenas quando criar
            if table_created and table_name:
                full_table_name = f"{schema}.{table_name}"
                cur.execute(f'ALTER TABLE {full_table_name} OWNER TO "{owner}";')
                conn.commit()
                print(f"[OK] Tabela {table_name} criada no banco {database}, owner={owner}")

        except Exception as e:
            conn.rollback()
            print(f"[ERRO] Falha ao criar tabela: {str(e)}")
            raise

        finally:
            cur.close()
            conn.close()


    def jdbc_url(self, database="sgs_bacen", schema="public"):
        """Retorna URL JDBC compatível com Spark."""
        return f"jdbc:postgresql://{self.host}:{self.port}/{database}?currentSchema={schema}"
