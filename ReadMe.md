# Intro

This reposistory is a example of a workflow using snakemake ([Link](https://snakemake.readthedocs.io/en/stable/index.html)) for doing an applied economics research project. Snakemake allows for defining input and outputs for each script defining the DAG or order of which scripts are supposed to be run. This eases reproducebility, because snakemake can check the workflow for changes further up the stream and whether scripts need to be rerun to ensure consistent output. It also forces you to define your intended input datasets of whathever work you're doing.
I've tried to set the structure up in a way that allows for divering paths to be created, so if you want do a subanalysis that may or may not end up in the main project, you can easily add a folder with this without messing up or having to redefine the entire pipeline.

This exampel incorporates Python and STATA scripts in a compatible way (so snakemake can call both programs and you don't for example have to redefine paths for both programs) but snakemake can make calls to the command line, you could also run different programs (although the path and input/output integration might require some extra work).

# Snakemake

Everytime you run snakemake, an overall logfile with error messages is created in the .snakemake/log folder

# Setup

## Environment

You need a conda enviroment, with snakemake installed.  Using `conda export --format=environment-yaml --file=envs/a313_snake.yaml` I've exported the enviroment I've used to the envs folder.

On the dst server this is less of a problem, since we can all access the same enviroment, and this can just be exported at the end.

For whatever environment is used, you need to install the project_setup file, as a package using:

`pip install -e .`

In the terminal after activating the environment and setting the working directory to the project folder (snakemake_example).

Then you can import project_setup from whatever directory (because it is referenced in pyproject.toml which installs it)

(This might also cause problems if you try to install the snakemake.yaml file, if it can't find this packages (because it is locally defined).

# Guide

DISCLAIMER: most of the guide was written by LLM, so it is a bit wordy, but I checked it for errors.

## Project Structure

The main folders are dgp (data generating process) and analysis, which together contain all the code for the project. The code is structured in multiple subfolders to these two folders. Each subfolder has a code folder, a logs folder, and an output folder. For the example there is only one code script to be run in each code folder, but you can define multiple if you want to.

## Snakemake Files and Structure

The snakemake workflow is defined across three files:

### Main Snakefile

The root `Snakefile` imports `project_setup` to create consistent file paths, includes the rule files from the `rules/` folder, and defines the master `all` rule that specifies the final outputs. It also includes a `make_dag` rule for generating visual representations of the workflow.

It also loads the config.yaml finds, which allows you to set parameters/options that are implemented in the scripts.

### Rule Files (rules/*.smk)

- `dgp.smk`: Contains rules for data generation (simulate, shocks)
- `analysis.smk`: Contains rules for analysis tasks (estimate, tables, stata_analysis)

Each rule file imports `project_setup` to ensure consistent file path management across the entire workflow.

## Project Setup Module (project_setup.py)

The `project_setup.py` module is the backbone of the project, providing several key functionalities:

### Path Management

- `create_paths_and_files()`: Creates consistent file paths for all project components
- `find_paths()`: Ensures paths are created only once and can be reused
- Automatically discovers project structure and creates paths for code, logs, and output folders
- Specific files you want to use for input and output needs to be defined manually in the `create_paths_and_files` function.

### Snakemake Integration with `file_setup()`:

- `file_setup()`: The main function called by Python scripts to initialize the snakemake environment. It calls mutliple sub-functions:
- `find_snakemake()`: Automatically detects whether the script is running through snakemake or interactively.
  - When run through snakemake: Uses the injected snakemake object.
  - When run interactively: Loads the appropriate rule configuration from the Snakefile
  - This allow seamless switching between running scripts through snakemake and interactive testing. And maintains consistent file paths and configurations in both modes.
- `try_inter()`: Which is called in `file_setup`, automatically enables IPython's autoreload magic for interactive development.
- Also sets up logging using the loguru package.

## Python Script Integration

Python scripts follow a consistent pattern for snakemake integration:

```python
import project_setup

# Initialize snakemake environment and logging
snake = project_setup.file_setup(rulename='rulename', log=True)

# Access parameters and file paths through the snake object
data = pd.read_csv(snake.input.input_file)
# ... processing ...
output.to_csv(snake.output.output_file)
```

### Key Features:

- **Automatic Rule Detection**: If no rulename is provided, it attempts to derive it from the filename
- **Dual Mode Operation**: Works both when called by snakemake and in interactive mode
- **Logging Setup**: Automatically configures loguru logging with timestamped log files
- **Path Consistency**: Ensures the same file paths are used whether running through snakemake or interactively

### Custom Package Imports

The project uses the `_import()` function to import custom modules while ensuring input dependencies are correctly tracked:

```python
# Import custom functions while maintaining snakemake dependency tracking
shocks_funcs = project_setup._import(snake.input.shocks_funcs)
```

This approach ensures that snakemake recognizes when dependency files change and reruns dependent rules accordingly.

## Stata Integration

Stata scripts are integrated through the `run_stata()` function in `project_setup.py` (which is called in a snakemake rule):

### How it Works:

1. **Rule Definition**: Stata rules in `analysis.smk` use the `run:` directive instead of `script:`
2. **Function Call**: `project_setup.run_stata(dofile, args)` is called with the do-file path and arguments
3. **Argument Passing**: Arguments are passed as command-line parameters to the Stata script, these are read by STATA as local macros with names 1, 2, 3, etc.
   the do file then uses the args command to name them.
4. **Local Variables**: A locals file is automatically created for direct Stata execution. (So you need to run stata through snakemake to create it).

### Stata Script Pattern:

```stata
* Check if running through Snakemake or directly
if missing(`"`1'"'){
    * Not running through Snakemake, use default paths
    include "stata_analysis_locals.do"
}

args logfile input_file output_file
log using "`logfile'", replace

* Your Stata code here using `input_file' and `output_file'
```

### Key Features:

- **Dual Mode Support**: Stata scripts work both when called by snakemake and when run directly
- **Automatic Logging**: Log files are automatically managed.
- **Path Consistency**: Input and output paths are passed as arguments from the snakefile, ensuring consistency with Python components

## Wildcard Rules for Document Generation

The workflow includes flexible wildcard rules for automatically generating PDF files from LaTeX and Markdown sources:

### LaTeX Compilation Rule (`compile_tex`)

```snakemake
rule compile_tex:
    input:
        project_setup.get_all_files_in_output,
        tex_file = "{folder}/{filename}.tex"
    output:
        pdf_file = "{folder}/{filename}.pdf"
```

**How it works:**

- **Automatic Discovery**: When snakemake needs a `.pdf` file, it automatically looks for a corresponding `.tex` file with the same name
- **Flexible Paths**: Uses wildcards `{folder}` and `{filename}` to work with any directory structure
- **Dependency Tracking**: Includes all files in the output folder as inputs, ensuring PDF regeneration when any dependency changes
- **LaTeX Compilation**: Uses `pdflatex` to compile the document

**Example Usage:** If your `all` rule requests `analysis/stata_analysis/stata_results_tex.pdf`, snakemake will automatically find `analysis/stata_analysis/stata_results_tex.tex` and compile it.

### Markdown Compilation Rule (`compile_md`)

```snakemake
rule compile_md:
    input:
        project_setup.get_all_files_in_output,
        md_file = "{folder}/{filename}.md"
    output:
        pdf_file = "{folder}/{filename}.pdf"
```

**How it works:**

- **Pandoc Integration**: Uses pandoc to convert Markdown files to PDF
- **Same Wildcard Pattern**: Follows the same flexible structure as the LaTeX rule
- **Directory Awareness**: Changes to the appropriate directory before compilation to handle relative paths correctly

### Key Features:

- **Wildcard Constraints**: Both rules use `filename="[^/\\\\]+"` to ensure filenames don't contain path separators
- **Automatic Dependency Management**: The `get_all_files_in_output()` function ensures that PDFs are regenerated when any file in the output directory changes
- **Seamless Integration**: These rules work automatically - you just need to specify the desired PDF output in your workflow

This approach allows you to focus on content creation while snakemake handles the compilation automatically, maintaining reproducibility and ensuring outputs are always up-to-date with their sources.

## Workflow Execution

The entire system is designed to work seamlessly whether you're:

1. **Running the full pipeline**: `snakemake -j4`
2. **Testing individual components**: Running Python scripts interactively in VS Code/Jupyter
3. **Debugging Stata code**: Running .do files directly in Stata

The `project_setup.py` module ensures that file paths, logging, and dependencies remain consistent across all execution modes, making development and debugging much easier while maintaining the reproducibility benefits of snakemake.

# Common runs

Activating the  a313_snake environment (or whathever the conda environment where snakemake is installed is called):

`conda activate a313_snake`

Running the snakerule called all (As I understand without a name you just run the first rule in the Snakefile):
`snakemake -j4`

If you want to run the snakefile with a specific target rule, you can specify it like this:

`snakemake -j4 <target_rule>`

using option `-f` to force the rule to run and `-F` to force all the rule's dependencies to also run.

To make a report of the project structure (inlcuding DAG and runtime for each script) run:

`snakemake --report report.html`

This is also done automatically in the all rule.

To just make the DAG, run:

`snakemake --forceall --dag | dot -Tpdf > dag.pdf`
