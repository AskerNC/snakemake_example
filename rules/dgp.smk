import project_setup
paths, files = project_setup.create_paths_and_files()

rule simulate:
    output:
        sim_data = files.sim_data
    params:
        n_obs = config["dgp"]["n_obs"],
        seed = config["dgp"]["seed"]
    script:
        files.simulate


rule shocks:
    input:
        sim_data = files.sim_data,
        shocks_funcs = files.shocks_funcs
    params:
        constant = config["dgp"]["constant"]
    output:
        sim_data_shocked = files.sim_data_shocked
    script:
        files.add_shocks
