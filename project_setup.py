
import inspect
import sys
import importlib
from types import SimpleNamespace
from pathlib import Path
from types import FrameType, ModuleType
from loguru import logger
from snakemake.rules import Rule
from snakemake.api import (
    SnakemakeApi, OutputSettings, ResourceSettings, StorageSettings
)
from snakemake.io import _IOFile, Wildcards, Resources, apply_wildcards

def create_paths_and_files() -> tuple[SimpleNamespace, SimpleNamespace]:
    """
    Creates a SimpleNamespace object containing all the files used in the project.
    This function is useful to ensure that the files are only created once and can be reused throughout.
    """
    paths = find_paths()

    files = SimpleNamespace()
    
    # setup files
    files.config = paths.root / "config.yaml"
    files.dgp_smk = paths.rules / "dgp.smk"
    files.analysis_smk = paths.rules / "analysis.smk"

    files.ado_example = paths.ado_files / "ado_example.ado"

    
    # Dgp files 
    files.sim_data = paths.simulate_baseline / "sim_data.csv"
    add_pyfile(files,'simulate', 'simulate_baseline')
    files.sim_data_shocked = paths.add_shocks / "sim_data_shocked.csv"

    add_pyfile(files,'add_shocks', 'add_shocks')
    add_pyfile(files,'shocks_funcs', 'add_shocks')

    

    # Analysis files
    files.estimates = paths.estimate_model / "estimates.txt"
    add_pyfile(files,'estimate', 'estimate_model')    
    files.final_tables = paths.make_tables / "final_tables.txt"
    add_pyfile(files,'tables', 'make_tables')
    files.stata_analysis = paths.stata_analysis_code / "stata_analysis.do"
    files.stata_results = paths.stata_analysis / "stata_results.tex"
    add_mdfile(files,'stata_results_md', 'stata_analysis')
    add_texfile(files,'stata_results_tex', 'stata_analysis')

    return paths,files

def add_mdfile(files: SimpleNamespace, name: str, foldername:str, namespacename: str = '') -> None:
    """
    Adds a Markdown file and corresponding pdf and log file to the files namespace.
    
    Args:
        files: The SimpleNamespace object containing the files.
        name: The name of the file to add.
        foldername: The name of the folder where the file is located. (this links to output folder inside that folder which is why we need .parent)
        namespacename: The name of the namespace to add the file to (optional and _md and _pdf will be added).
    """
    paths = find_paths()
    if namespacename == '':
        # simply name it the same as name
        namespacename = name

    for ext in ['md', 'pdf']:
    # , 'log'
        setattr(files, f'{namespacename}_{ext}', getattr(paths,f'{foldername}').parent / f'{name}.{ext}')


def add_texfile(files: SimpleNamespace, name: str, foldername:str, namespacename: str = '') -> None:
    """
    Adds a TeX file and corresponding pdf and log file to the files namespace.
    
    Args:
        files: The SimpleNamespace object containing the files.
        name: The name of the file to add.
        foldername: The name of the folder where the file is located.
        namespacename: The name of the namespace to add the file to (optional and _tex and _pdf will be added).
    """
    paths = find_paths()
    if namespacename == '':
        # simply name it the same as name
        namespacename = name

    for ext in ['tex', 'pdf']:
        setattr(files, f'{namespacename}_{ext}', getattr(paths,f'{foldername}').parent / f'{name}.{ext}')

def add_pyfile(files: SimpleNamespace, name: str, foldername:str, namespacename: str = '') -> None:
    """
    Adds a Python file to the files namespace.
    Also adds the corresponding log file to the logs namespace.
    
    Args:
        files: The SimpleNamespace object containing the files.
        name: The name of the file to add.
        foldername: The name of the folder where the file is located.
        namespacename: The name of the namespace to add the file to (optional).
    """
    paths = find_paths()
    if namespacename == '':
        # simply name it the same as name
        namespacename = name

    setattr(files, namespacename, getattr(paths,f'{foldername}_code') / f'{name}.py')
    
    # logfiles are not added into snakemake, instead loguru is allowed to change their name dependent on time
    #setattr(files, f'{namespacename}_log', getattr(paths,f'{foldername}_logs') / f'{name}.log')


def file_setup(
    rulename: str = '',
    log: bool = True,
    wildcards: dict | None = None,
):
    """
    Set up the file for the given rule name. If no rule name is provided, it will use the stem of the current file.
    Also tries to activate the autoreload magic command in IPython if running in an interactive window.
    Args:
        rulename: The name of the rule to set up. If not provided, it defaults to the stem of the current file.
        log: Whether to set up logging for the rule. Defaults to True.
        wildcards: Optional dict of concrete wildcard values. Required when the
            rule's input/output use wildcards (e.g. compile_tex: pass
            ``wildcards={'folder': 'analysis/foo', 'filename': 'bar'}``).
    Returns:
        A Snakemake Rule object, or an _InteractiveSnakemake wrapper when
        wildcards were supplied and the rule has wildcards.
    """

    try_inter()

    # Find the snakemake object for the given rule name
    # Get the caller's frame to access their global variables
    caller_frame = inspect.currentframe().f_back
    snakemake = find_snakemake(rulename, caller_frame=caller_frame, wildcards=wildcards)
    
    if log:
        
        # Setup logging
        logger.remove()
        
        # add logs to normal output 
        logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")

        # add a log file to the logs folder
        # get folder and log name from the snakemake object
        if hasattr(snakemake, 'script'):
            # Use the parent directory of the script as the log folder
            # This is true when snakemake is loaded from the snakefile
            base_folder = snakemake.script.parent.parent
            log_name = str(snakemake)
        else:
            # Fallback to the root folder if script is not available
            # This is true when snakemake comes from running the script through snakemake
            base_folder = Path(snakemake.scriptdir).parent
            log_name = str(snakemake.rule)


        logger.add(base_folder / 'logs' / (log_name + '_{time:YYYY-MM-DD_HH-mm}.log'),
                format="{time} {level} {message}",
                level="INFO",
                retention = 3, # Keep the last 3 log files
                )
        logger.info(f"Snakemake object loaded for rule: {log_name}")

    return snakemake


def try_inter() -> None:
    """
    Runs the autoreload magic command in IPython if running in an interactive window.
    This allows for automatic reloading of modules when they are modified, which is useful for
    development and testing purposes.
    """
    try:
        from IPython import get_ipython

        ip = get_ipython()
        if ip is not None:
            ip.run_line_magic("load_ext", "autoreload")
            ip.run_line_magic("autoreload", "2")
    except ImportError:
        pass

def _import(module_path: str | Path | _IOFile ) -> ModuleType:
    """
    Imports a module from a given file path.
    Should be similar to import <module_name> but works with a file path.

    Args:
        module_path: The path to the module file. It can be a string, Path object, or _IOFile object.
    
    Returns:
        The imported module.
    """
    path_obj = Path(module_path)
    sys.path.append(str(path_obj.parent))
    return importlib.import_module(path_obj.stem)

def create_paths() -> SimpleNamespace:
    """
    Defines and returns a namespace containing paths for the project root, data, and output directories.
    The project root is determined by finding the parent directory of the current file's location.
    """
    paths = SimpleNamespace()

    # This is technically overkill because the file is always project_setup.py
    paths.root = find_project_root(__file__)


    # Add theme folders
    for themename in ['analysis','dgp']:
        themefolder = paths.root / themename
        setattr(paths, themename, themefolder)
        
        subfolders = find_all_folders(themefolder)
        i = 0
        while i < len(subfolders):
            subfolder = subfolders[i]
            sub_subfolders = find_all_folders(subfolder)
            if 'code' in [sub_subfolder.name for sub_subfolder in sub_subfolders]:
                # If the subfolder has a code folder, assume it is a code folder
                setattr(paths, subfolder.name, subfolder / "output")
                setattr(paths, subfolder.name + "_code", subfolder / "code")
                setattr(paths, subfolder.name + "_logs", subfolder / "logs")
            else:
                # Otherwise, assume it contains multiple folders who each have their own output, code and logs folders
                setattr(paths, subfolder.name, subfolder)
                subfolders.extend(sub_subfolders)

            i += 1

    # Add other folders and all their subfolders
    for folder in ['rules','utils']:
        folder_path = paths.root / folder
        setattr(paths, folder, folder_path)
        subfolders = find_all_folders(folder_path)
        for subfolder in subfolders:
            setattr(paths, subfolder.name, subfolder)

    return paths


def find_paths()-> SimpleNamespace:
    """
    Checks if paths have already been created, and if not, creates them.
    This function is useful to ensure that the paths are only created once and can be reused throughout 
    (I think it only works when paths is explcitly defined in the global scope).
    """
    if "paths" in globals():
        return paths # type: ignore  # noqa: F821
    else:
        return create_paths()

def find_all_folders(path: str | Path) -> list[Path ]:
    """Get all folders in the path"""
    if isinstance(path, str):
        path = Path(path)
    return [Path(folder) for folder in path.iterdir() if folder.is_dir()]

def find_all_files(path: str | Path) -> list[Path ]:
    """Get all files in the path"""
    if isinstance(path, str):
        path = Path(path)
    return [Path(file) for file in path.iterdir() if file.is_file()]


def get_all_files_in_output(wildcards):
    '''
    For use in Snakemake to get all files in the output folder.
    '''
    folder_path = Path(wildcards.folder)
    output_path = folder_path / "output"
    
    # Convert Path objects to strings with forward slashes for Snakemake
    return [str(file).replace("\\", "/") for file in output_path.iterdir() if file.is_file()]
    


def create_stata_paths() -> None:
    """
    Create a do file for stata defining the paths used in the project.
    (not used)
    """
    paths = find_paths()
    do_file = paths.root / "create_paths.do"
    with open(do_file, "w") as f:
        for attr in dir(paths):
            if not attr.startswith("_"):
                f.write(f"global {attr} \"{getattr(paths, attr)}\"\n")
    return do_file

class _InteractiveSnakemake:
    """
    A snakemake-like object built from a Rule + concrete wildcard values.
    Mimics the namespace that scripts get when run via `snakemake` proper,
    so interactive sessions can use snake.input.x / snake.output.y / etc.
    """
    def __init__(self, rule, input_, output, params, wildcards, log, config):
        self.rule = rule.name
        self.input = input_
        self.output = output
        self.params = params
        self.wildcards = wildcards
        self.log = log
        self.threads = 1
        self.resources = Resources(fromdict={"_cores": 1})
        self.config = config

        # rule.script may itself contain wildcards (e.g. "{folder}/code/foo.py").
        # Expand it so file_setup's logging block can compute a real folder path.
        script = getattr(rule, "script", None)
        if script is not None:
            try:
                script_str = apply_wildcards(str(script), wildcards)
            except Exception:
                script_str = str(script)
            self.script = Path(script_str)
            self.scriptdir = self.script.parent
        else:
            # Shell-only rules don't normally call file_setup, but provide a
            # sensible fallback so log=True doesn't crash. Project convention:
            # "<folder>/code" sits next to "<folder>/logs".
            folder = getattr(wildcards, "folder", None)
            if folder is None and len(output) > 0:
                folder = str(Path(str(output[0])).parent.parent)
            self.scriptdir = Path(folder) / "code" if folder else Path(".")

    def __str__(self):
        return self.rule


class _JobProxy:
    """Stand-in for Job in Rule.expand_params — it only reads .resources / ._cores."""
    @property
    def resources(self):
        return Resources(fromdict={"_cores": 1})


def _required_wildcards(rule: Rule) -> set[str]:
    required: set[str] = set()
    for f in list(rule.output) + [g for g in rule.input if isinstance(g, _IOFile)]:
        required.update(f.get_wildcard_names())
    return required


def _build_interactive_snakemake(
    rule: Rule, wildcards: dict, config: dict
) -> "_InteractiveSnakemake":
    required = _required_wildcards(rule)
    missing = required - set(wildcards)
    if missing:
        raise ValueError(
            f"Rule '{rule.name}' needs wildcards {sorted(required)}; "
            f"missing values for: {sorted(missing)}"
        )
    extra = set(wildcards) - required
    if extra:
        logger.warning(
            f"Wildcards passed but not used by rule '{rule.name}': {sorted(extra)}"
        )

    input_, *_ = rule.expand_input(wildcards)
    output, _ = rule.expand_output(wildcards)
    log_ = rule.expand_log(wildcards)
    try:
        params, _ = rule.expand_params(
            wildcards, input_, output, _JobProxy(), omit_callable=False
        )
    except Exception as e:
        logger.warning(
            f"Could not fully expand params for '{rule.name}': {e}. "
            "Falling back to omit_callable=True."
        )
        params, _ = rule.expand_params(
            wildcards, input_, output, _JobProxy(), omit_callable=True
        )

    return _InteractiveSnakemake(
        rule=rule,
        input_=input_,
        output=output,
        params=params,
        wildcards=Wildcards(fromdict=wildcards),
        log=log_,
        config=config,
    )


def load_rule(
    rulename: str,
    snakefile: Path | str = Path('Snakefile'),
    wildcards: dict | None = None,
) -> Rule | _InteractiveSnakemake:
    """
    Load a Snakemake rule from the specified path.

    Args:
        rulename: The name of the rule to load.
        snakefile: The path to the Snakefile. Defaults to 'Snakefile'.
        wildcards: Optional dict of concrete wildcard values. If provided and
            the rule has wildcards, returns an _InteractiveSnakemake whose
            input/output/params/wildcards are fully expanded. Expansion is
            performed inside the SnakemakeApi context so the workflow stays
            alive while Rule.expand_* methods walk back into rule.workflow.
    """
    with SnakemakeApi(OutputSettings(verbose=False)) as smk_api:
        wf_api = smk_api.workflow(
            resource_settings=ResourceSettings(cores=1),
            storage_settings=StorageSettings(),
            snakefile=snakefile,
        )

        #get the underlying Workflow object (lazy-loaded)
        wf = wf_api._workflow

        for rule in wf.rules:
            if rule.name == rulename:
                if wildcards is None:
                    return rule
                return _build_interactive_snakemake(rule, wildcards, dict(wf.config))

    raise ValueError(f"Rule '{rulename}' not found in the Snakefile at {snakefile}.")

def find_snakemake(
    rulename: str = '',
    caller_frame: None | FrameType = None,
    wildcards: dict | None = None,
) -> Rule | _InteractiveSnakemake:
    '''
    Find snakemake rule configuration. If not run through snakemake,
    (so for example running this script directly in interactive mode),
    it will load the configuration from the snakefile in the root folder.
    Args:
        rulename: The name of the rule to find. If not provided, it defaults to the stem of the current file.
        caller_frame: The frame of the caller, used to check if snakemake is already defined.
            It is useful when this function is called from another function that is not defined in main running script.
            As this is the place where it finds globals from.
        wildcards: Optional dict of concrete wildcard values for rules that
            use wildcards. Required when the rule has wildcards; ignored when
            running through snakemake itself (the injected object wins).
    Returns:
        A Snakemake Rule object, or an _InteractiveSnakemake wrapper when
        wildcards were supplied and the rule has wildcards.
    '''

    if caller_frame is None:
        # Get the caller's frame to access their global variables
        caller_frame = inspect.currentframe().f_back
    caller_globals = caller_frame.f_globals

    print("Checking for snakemake object...")

    # When snakemake runs a script, it injects the snakemake object directly
    # into the script's global namespace
    try:
        snakemake_obj = caller_globals['snakemake']
        print("Snakemake object found in globals")
        return snakemake_obj
    except (KeyError):
        print('Snakemake object not found or invalid, loading from snakefile')

    # If snakemake object not found, load from snakefile
    # Determine the rule name
    if rulename == '':
        # Get the caller's filename to derive the rulename
        # This generally doesn't work as it often results in project_setup or ipython obejct
        caller_file = caller_frame.f_code.co_filename
        rulename = Path(caller_file).stem
        print(f'Derived rulename from file: {rulename}')

    paths = find_paths()

    # Find snakemake configuration
    snakemake_obj = load_rule(
        rulename, snakefile=paths.root / "Snakefile", wildcards=wildcards
    )
    print(f'Loaded rule {rulename} from snakefile')

    # If the user did not supply wildcards but the rule has some, fail loudly
    # rather than returning unexpanded "{folder}/..." strings.
    if wildcards is None and isinstance(snakemake_obj, Rule):
        required = _required_wildcards(snakemake_obj)
        if required:
            raise ValueError(
                f"Rule '{rulename}' has wildcards {sorted(required)}. "
                f"Pass file_setup(rulename='{rulename}', "
                f"wildcards={{{', '.join(repr(w) + ': ...' for w in sorted(required))}}})."
            )

    return snakemake_obj



def run_stata(dofile, args={},logfilename='',ado_files: None|list|str = None,snakeobjects: list[None|dict] = [None]) -> None:
    import stata_setup
    stata_setup.config(r'C:\Program Files\Stata18/', 'mp')
    from pystata import stata # type: ignore
    dofile = Path(dofile)
    

    
    
    if logfilename=='':
        logfilename = f'{dofile.stem}'
    logfile = dofile.parent.parent / 'logs' / f'{logfilename}.log'

    
    ## Not plan: make the locals file also name the locals explicitly
    # the just run the local do file before running the do file

    # Write a locals file with args in the do file's directory for when running through stata directly 
    locals_file = dofile.parent / f'{dofile.stem}_locals.do'

    with open(locals_file, 'w') as f:
        f.write(f'local logfile "{logfile}"\n')

        for snakeobject in snakeobjects:
            if snakeobject is not None:
                args.update(snakeobject.__dict__) 

        for key,value in args.items():
            f.write(f'local {key} "{value}"\n')

        if ado_files:
            if type(ado_files) is str:
                ado_files = [ado_files]
            
            dirs = {str(Path(f).parent) for f in ado_files}   # unique dirs
            for d in dirs:
                # Note: this simply adds the path of the ado files, so any ado file from that path can technically be used
                f.write(f'adopath ++ "{d}"\n')     # project ado wins over SSC

    return stata.run(fr'do "{dofile}" "{dofile.parent}\\"', )


class ProjectRootNotFoundError(FileNotFoundError):
    def __init__(self) -> None:
        super().__init__("Project root not found. No markers found in any parent directories.")


class InvalidStartPathTypeError(TypeError):
    def __init__(self, start_path: str | Path) -> None:
        super().__init__(f"start_path must be a string or Path object, not {type(start_path)}")


class StartPathResolutionError(FileNotFoundError):
    def __init__(self, start_path: str | Path) -> None:
        super().__init__(f"The starting path '{start_path}' does not exist or could not be resolved.")


def find_project_root(start_path: str | Path, markers: list[str] | None = None) -> Path:
    """
    Finds the project root directory by searching upwards from a starting path
    for specific marker files or directories.

    Args:
        start_path: The path to a file or directory within the project.
                    It's recommended to pass `__file__` from the calling script
                    to ensure the search starts relative to that script's location.
        markers: A list of filenames or directory names that indicate the
                 project root. If None, uses a default list:
                 ['.git', 'pyproject.toml', 'setup.py', '.project_root',
                  'requirements.txt', 'manage.py'].

    Returns:
        A Path object representing the absolute path to the project
        root directory if found, otherwise None.

    Raises:
        FileNotFoundError: If the provided start_path does not exist.
        TypeError: If start_path is not a string or Path object.
    """
    if markers is None:
        # Common markers for various project types
        markers = [
            ".git",  # Git repository root
            "pyproject.toml",  # Standard Python project config
            "setup.py",  # Older Python project config
            ".project_root",  # Custom marker file
            "requirements.txt",  # Common dependency file often at root
            "manage.py",  # Django project root marker
            # Add other markers relevant to your projects if needed
        ]

    # Ensure start_path is an absolute Path object and exists
    if not isinstance(start_path, str | Path):
        raise InvalidStartPathTypeError(start_path)
    try:
        # Use resolve() to get the absolute path and resolve any symlinks
        search_path = Path(start_path).resolve(strict=True)
    except FileNotFoundError as err:
        raise StartPathResolutionError(start_path) from err

    # If start_path is a file, begin the search from its parent directory
    current_dir = search_path.parent if search_path.is_file() else search_path

    # Traverse upwards looking for markers
    while True:
        # Check if any marker exists in the current directory
        for marker in markers:
            if (current_dir / marker).exists():
                return current_dir  # Found the root

        # Move up to the parent directory
        parent_dir = current_dir.parent
        # Check if we have reached the filesystem root
        if parent_dir == current_dir:
            # This happens when current_dir is the root directory (e.g., '/')
            # or if permission errors prevent accessing higher directories.
            raise ProjectRootNotFoundError()

        current_dir = parent_dir
