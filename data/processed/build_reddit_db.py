import sqlite3
import pandas as pd

# ======= CONFIG =======
csv_file = 'comments_cleaned.csv'      # CSV filename
db_file  = 'reddit_data.db'            # output SQLite database filename
table    = 'reddit'                    # table name

# ======= LOAD CSV =======
df = pd.read_csv(csv_file)

# ======= CREATE DATABASE =======
conn = sqlite3.connect(db_file)

# ======= WRITE TABLE =======
df.to_sql(table, conn, if_exists='replace', index=False)

conn.close()

print(f"✅ Done! CSV has been converted into a SQLite database: {db_file}")
print(f"✅ Table name: {table}")
print("You can now query it using sqlite CLI or any SQL client.")
