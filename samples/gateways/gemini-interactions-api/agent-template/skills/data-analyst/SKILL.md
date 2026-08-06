# Data Analyst

Query BigQuery via the `bigquery` MCP tool and analyse the rows with pandas.

## Recipe

1. **Query.** Call the `bigquery` MCP tool's `execute_sql` with a
   fully-qualified table name, e.g.
   ``SELECT region, SUM(revenue) AS revenue FROM `proj.demo.q4_sales` GROUP BY region``.
   Use `get_table_info` first if you need the schema.

2. **Load.** The tool returns rows as JSON. In the sandbox, install once
   then convert:

   ```python
   # pip install -q pandas tabulate   (run as a shell step first)
   import pandas as pd
   df = pd.DataFrame(rows)
   for c in ("revenue", "units"):
     if c in df:
       df[c] = pd.to_numeric(df[c])
   ```

3. **Answer.** State the headline number first, then a short markdown
   table (`df.to_markdown(index=False)`) of the supporting rows. Keep
   the prose under three sentences.
