import project_setup
paths, files = project_setup.create_paths_and_files()

rule estimate:
    input:
        sim_data_shocked = files.sim_data_shocked
    output:
        estimates = files.estimates
    script:
        files.estimate


rule tables:
    input:
        estimates = files.estimates
    output:
        final_tables = files.final_tables
    script:
        files.tables


rule stata_analysis:
    input:
        sim_data_shocked = files.sim_data_shocked,
        stata_analysis_code = files.stata_analysis,
        ado_example = files.ado_example
    output:
        stata_results = files.stata_results
    run:
        project_setup.run_stata(f'{input.stata_analysis_code}',{**input.__dict__,**output.__dict__},
                                ado_files=[input.ado_example],
                                )

#snakemake stata_analysis -j 1 -f