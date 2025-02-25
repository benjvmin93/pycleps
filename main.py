import argparse
from cleps import ClepsSSHWrapper
from pathlib import Path
from helpers import SlurmOptions, SbatchHeader

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Cleps Job Submission Tool")
    parser.add_argument("--username", help="Your Cleps username")
    parser.add_argument("--repo", required=True, help="Repository address (e.g., git@github.com:user/repo.git)")
    parser.add_argument("--wd", default="wd", help="Working directory where the git repo will be copied (default: 'wd')")
    parser.add_argument("--script", required=True, help="The name of the script in the git repo that will be run on the cluster")
    
    args = parser.parse_args()

    # Extract arguments
    username = args.username
    repo_addr = args.repo
    working_dir = args.working_dir
    script_name = args.script_name

    repo_name = repo_addr
    if repo_addr.startswith("https://") or repo_addr.startswith("git@github.com"):
        repo_name = repo_addr.split("/")[-1].replace(".git", "")

    working_dir = Path(working_dir)
    repo_path = working_dir / repo_name

    # Initialize ClepsSSHWrapper
    client = ClepsSSHWrapper("cleps.inria.fr", username=username)

    try:
        # Clone the repository and return the path of the script that will be run
        script_path = client.clone_repo(repo_addr=repo_addr, dst_dir=working_dir, script_name=script_name)

        # Define Slurm options
        slurm_options = SlurmOptions(
            job_name=f"{script_name.split('.')[0]}",
            output=f"{working_dir}/outputs"
        )
        sbatch_options = SbatchHeader(account=username)

        client.send_job(
            run_cmd=f"python {script_path}",
            working_dir=working_dir,
            slurm_options=slurm_options,
            sbatch_options=sbatch_options
        )
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
