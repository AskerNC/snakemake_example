# tables.py
import project_setup

snake = project_setup.file_setup(rulename='tables')


# For simplicity, copy the estimates into a "final table" format
with open(snake.input.estimates, "r") as fin, open(snake.output.final_tables, "w") as fout:
    lines = fin.readlines()
    
    # Write a basic table header
    fout.write("=== MODEL SUMMARY TABLE ===\n\n")
    
    # Write selected lines or all lines from model summary
    for line in lines[:20]:  # you can customize this
        fout.write(line)
