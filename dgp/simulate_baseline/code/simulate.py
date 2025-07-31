import pandas as pd
import numpy as np
import project_setup
from loguru import logger 

# Find the snakemake object for the given rule name and set up logging
snake = project_setup.file_setup(rulename='simulate',log=True)

# Set up rng
rng = np.random.default_rng(seed = snake.params.seed)


# Simulate some data
df = pd.DataFrame({
    "x": rng.random(snake.params.n_obs),
    "y": rng.random(snake.params.n_obs)
})

logger.info(f'DataFrame:\n{df}')


df.to_csv(snake.output.sim_data, index=False)

logger.success("Simulate finished")