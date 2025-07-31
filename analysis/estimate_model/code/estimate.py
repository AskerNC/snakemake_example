import pandas as pd
import statsmodels.api as sm
import project_setup

snake = project_setup.file_setup(rulename='estimate')

df = pd.read_csv(snake.input.sim_data_shocked)
X = sm.add_constant(df["x"])
y = df["y"]
model = sm.OLS(y, X).fit()
with open(snake.output.estimates, "w") as f:
    f.write(model.summary().as_text())
