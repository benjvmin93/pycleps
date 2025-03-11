import argparse
from pycleps.cleps_ssh_wrapper import ClepsSSHWrapper
from pathlib import Path
from pycleps.helpers import SlurmOptions, SbatchHeader
import asyncio

def validate_numbers(input_list: list[str]):
    """
    Validate that all elements in a list of strings are either all integers or all floats.
    Raises a ValueError if there's a mix or invalid input.

    Returns the converted python list.
    """
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

    # If not all are ints or all are floats, raise an error
    if not (all_ints or all_floats):
        raise ValueError("Input list must contain only integers or only floats.")
    
    return [int(x) for x in input_list] if all_ints else [float(x) for x in input_list]

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Cleps Job Submission Tool")
    parser.add_argument("--username", help="Your Cleps username")
    parser.add_argument("--repo", required=True, help="Repository address (e.g., git@github.com:user/repo.git)")
    parser.add_argument("--wd", default=".", help="Working directory where the git repo will be copied (default: '.')")
    parser.add_argument("--script", required=True, help="The command that will be used to run your script")
    parser.add_argument("--env", required=False, help="The command that will be used to set your jobs in the right environment. The environment should already be created within the cluster.")
    parser.add_argument("--cpus-per-task", default="", required=False, help="Number of cpus required to run your simulations")
    parser.add_argument("--wait", required=False, action='store_true', help="Whether or not the program will wait for job to end before exiting")
    parser.add_argument("--array", required=False, help="Different parameters to run your experiments with in parallel. Either a list of arguments a,b,c or a range a-b")

    args = parser.parse_args()

    # Extract arguments
    username = args.username
    repo_addr = args.repo
    working_dir = args.wd
    script = args.script
    env_cmd = args.env
    cpus_per_tasks = args.cpus_per_task
    array = args.array

    if array:
        if "-" in array:    # If range
            try:
                start, end = map(int, array.split("-"))
                array = list(range(start, end + 1))
            except ValueError:
                raise argparse.ArgumentTypeError(f"Invalid range format: {array_value}. Expected format: a-b")
        else:   # If list of the form a,b,c,d...
            array = array.split(",")
            array = validate_numbers(array)

    wait = False
    if args.wait:
        wait = True

    repo_name = repo_addr   # Parse repository name
    is_git_repo = False
    if repo_addr.startswith("https://") or repo_addr.startswith("git@github.com"):
        repo_name = repo_addr.split("/")[-1].replace(".git", "")
        is_git_repo = True
    else:
        repo_name = "".join(repo_name.split("/")).strip()

    working_dir = Path(working_dir)
    repo_path = working_dir / repo_name

    # Initialize ClepsSSHWrapper
    client = ClepsSSHWrapper("cleps.inria.fr", username=username)
    client.exec_cmd(f"mkdir -p {working_dir}")

    try:
        # Clone the repository
        client.clone_repo(repo_addr=repo_addr, dst_dir=repo_path)

        # Define Slurm options
        outputs = repo_path / "outputs"
        slurm_options = SlurmOptions(
            array=True if array else False,
            job_name=repo_name,
            cpus_per_task=cpus_per_tasks,
            output=outputs,
        )
        sbatch_options = SbatchHeader(array=array, wait=wait)

        jobId = client.send_job(
            run_cmd=script,
            working_dir=repo_path,
            slurm_options=slurm_options,
            sbatch_options=sbatch_options,
            env_cmd=env_cmd
        )


        if wait:    # If slurm waited for the jobs to end, we can directly fetch the results with scp
            output_paths = client.get_output(repo_path, jobId)
            client.fetch_outputs(jobs=output_paths, local_path=f"{repo_name}/outputs/" if is_git_repo else repo_addr)

    except Exception as e:
        print(f"An error occurred: {e}")

def run():
    main()