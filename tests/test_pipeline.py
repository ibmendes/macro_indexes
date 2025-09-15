# %%
### simples teste antes de alimentar o banco de dados 

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from utils.sgs.sgs_index import get_sgs_index
from main import Main

# cria instância do Main
main = Main(app_name="teste", host="localhost", port=5432, database="sgs_bacen")

# %% 

# usa spark e conector da instância
df = get_sgs_index(
    main.spark,
    main.connector,
    433,
    'ipca'
)

df.show(5, truncate=False)

### teste de recursividade 
df = get_sgs_index(
    main.spark,
    main.connector,
    12,
    'cdi'
)

df.show(5, truncate=False)
# %%
# alimentando histórico

## igp - m 
df = get_sgs_index(
    main.spark,
    main.connector,
    189,
    'IGPM',
    "raw",
    '1994-01-01',
    '2004-12-01'
)

df = df.orderBy(df["data"].asc())
df.show(5, truncate=False)

if df.count() > 0:
    main.write_df(df, "igpm", "raw", "append")
# %%

from bcb import sgs 

df = sgs.get(189, last=10)


# mostra os primeiros registros
print(df.head())
print(df.info())

# %%
# %%
# alimentando histórico
df = get_sgs_index(
    main.spark,
    main.connector,
    189,
    'igpm',
    "raw",
    '2025-02-01',
    '2025-09-01'
)

df = df.orderBy(df["data"].desc())
df.show(5, truncate=False)

if df.count() > 1:
    main.write_df(df, "igpm", "raw", "append")

# %%
# main trigger
main.run()
# %%
