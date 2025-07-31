# Snakefile for the data generation and analysis pipeline
import glob
import project_setup
from pathlib import Path

paths, files = project_setup.create_paths_and_files()

configfile: files.config

# Include the rule files
include: files.dgp_smk
include: files.analysis_smk

# Run all rules to get the final output (can be redefined as needed)
rule all:
    input:
        stata_results_md = files.stata_results_md_pdf,
        stata_results_pdf = files.stata_results_tex_pdf,
        final_tables = files.final_tables,
        dag = "dag.pdf",
    output:
        report = "report.html",
    shell:
        """
        snakemake --report {output.report}
        """


rule make_dag:
    input:
        # Main Snakefile
        snakefile = "Snakefile",
        # Included rule files
        dgp_rules = files.dgp_smk,
        analysis_rules = files.analysis_smk,
        # Configuration file
        config_file = files.config,
        # Project setup module (since it defines file paths and structure)
        project_setup = "project_setup.py"
    output:
        dag = "dag.pdf",
    shell:
        """
        snakemake --forceall --dag | dot -Tpdf > {output.dag}
        """


# To run this rule write snakemake -j1 in the command line (because it is the first rule)


# General wildcard tex rule:
rule compile_tex:
    '''
    This rule compiles a LaTeX file to PDF
    using pdflatex. It is designed to be flexible for different folders and filenames.
    So defining a rule with .pdf file as input (for example in the all rule), will cause stata too look for a .tex file with the same name
    and try to run run this rule to create the pdf using everything in the output folder in the same folder as input
    '''
    wildcard_constraints:
        filename="[^/\\\\]+"  # Ensure filename doesn't contain / or \ (path separators)
    input:
        # Everything in the output directory of the folder
        project_setup.get_all_files_in_output,

        # The tex file to compile
        tex_file = "{folder}/{filename}.tex"
    output:
        # The corresponding PDF file
        pdf_file = "{folder}/{filename}.pdf"
    shell:
        """
        pdflatex -output-directory={wildcards.folder} {input.tex_file}
        """

# General wildcard markdown md rule:
rule compile_md:
    wildcard_constraints:
        filename="[^/\\\\]+"  # Ensure filename doesn't contain / or \ (path separators)
    input:
        project_setup.get_all_files_in_output,
        md_file = "{folder}/{filename}.md"
    output:
        pdf_file = "{folder}/{filename}.pdf"
    #params:
        #input_dir = lambda wildcards, input: Path(input.md_file).parent, # a way to access parent of the md file
    shell:
        """
        cd {wildcards.folder} && pandoc {input.md_file} -o {output.pdf_file}
        """
