import typer
from pycleps.cleps_ssh_wrapper import ClepsSSHWrapper
from pathlib import Path
from pycleps.helpers import SlurmOptions, SbatchHeader
from git import Repo
import logging
from typing import Optional

logging.basicConfig(filename="pycleps.log", encoding="utf-8", level=logging.INFO)
logger = logging.getLogger(__name__)

app = typer.Typer()

def validate_numbers(input_list: list[str]):
    def is_int(s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def is_float(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    all_ints = all(is_int(x) for x in input_list)
    all_floats = all(is_float(x) for x in input_list)

    if not (all_ints or all_floats):
        raise ValueError("Input list must contain only integers or only floats.")

    return [int(x) for x in input_list] if all_ints else [float(x) for x in input_list]

def github_branches(repo: str):
    return [str(b) for b in Repo(repo).branches]

@app.command()
def submit(
    repo: str = typer.Argument(..., help="Repository address (e.g., git@github.com:user/repo.git)"),
    branch: Optional[str] = typer.Option(None, help="Repository branch you want to use", autocompletion=github_branches),
    user: Optional[str] = typer.Option(None, help="Your Cleps username"),
    wd: str = typer.Option(".", help="Working directory where the git repo will be copied"),
    script: Optional[str] = typer.Option(None, help="Command to run your script"),
    env: Optional[str] = typer.Option(None, help="Path of the conda environment .yml file"),
    name: str = typer.Option("pycleps-env", help="Name of the environment inside the cluster"),
    setup: Optional[str] = typer.Option(None, help="Command to install required packages"),
    cpt: Optional[str] = typer.Option("", help="Number of CPUs required for simulations"),
    wait: bool = typer.Option(False, help="Wait for job completion before exiting"),
    array: Optional[str] = typer.Option(None, help="Parameters for parallel experiments (list or range)"),
    time: Optional[str] = typer.Option("", help="Time limit for simulations"),
):
    wd_path = Path(wd)
    repo_name = Path(repo).name.replace(".git", "")
    repo_path = wd_path / repo_name
    
    client = ClepsSSHWrapper(wd=wd_path, username=user)

    if array:
        if "-" in array:
            try:
                start, end = map(int, array.split("-"))
                array = list(range(start, end + 1))
            except ValueError:
                typer.echo("Invalid range format. Use a-b.", err=True)
                raise typer.Exit(code=1)
        else:
            array = validate_numbers(array.split(","))
    
    client.clone_repo(repo_addr=repo, dst_dir=repo_path, git_branch=branch)
    client.setup_env(env_install_cmd=setup, env_file=env, env_name=name, repo_path=repo_path)
    
    slurm_options = SlurmOptions(array=bool(array), job_name=repo_name, cpus_per_task=cpt, output=repo_path / "outputs", time=time)
    sbatch_options = SbatchHeader(array=array, wait=wait)
    
    job_id = client.send_job(run_cmd=script, working_dir=repo_path, slurm_options=slurm_options, sbatch_options=sbatch_options, env_name=name)
    
    if wait:
        client.fetch(job_id, repo_path)

@app.command()
def fetch(
    repo: Path = typer.Argument(..., help="Remote repository path on the cluster"),
    job_id: str = typer.Argument(..., help="Job ID to fetch results for"),
    user: Optional[str] = typer.Option(None, help="Your Cleps username"),
):
    client = ClepsSSHWrapper(wd=Path(), username=user)
    client.fetch(jobId=job_id, remote_path=repo)

if __name__ == "__main__":
    app()
