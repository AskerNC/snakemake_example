import pandas as pd
import project_setup
from loguru import logger

# Find the snakemake object for the given rule name
snake = project_setup.file_setup(rulename='shocks')

# Import local functions from shocks_funcs.py
shocks_funcs = project_setup._import(snake.input.shocks_funcs)



# Test the import
shocks_funcs.test_function()

df = pd.read_csv(snake.input.sim_data)
df["y"] += snake.params.constant  # Add a constant "shock"

logger.info(f"Applied shock with constant: {snake.params.constant}")

df.to_csv(snake.output.sim_data_shocked, index=False)