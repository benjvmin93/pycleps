import argparse
from cleps import ClepsSSHWrapper
from pathlib import Path
from helpers import SlurmOptions, SbatchHeader

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Cleps Job Submission Tool")
    parser.add_argument("--username", help="Your Cleps username")
    parser.add_argument("--repo", required=True, help="Repository address (e.g., git@github.com:user/repo.git)")
    parser.add_argument("--wd", default=".", help="Working directory where the git repo will be copied (default: '.')")
    parser.add_argument("--script", required=True, help="The command that will be used to run your script")
    parser.add_argument("--env", required=False, help="The command that will be used to set your jobs in the right environment. The environment should already be created within the cluster.")
    
    args = parser.parse_args()

    # Extract arguments
    username = args.username
    repo_addr = args.repo
    working_dir = args.wd
    script = args.script
    env_cmd = args.env

    repo_name = repo_addr
    if repo_addr.startswith("https://") or repo_addr.startswith("git@github.com"):
        repo_name = repo_addr.split("/")[-1].replace(".git", "")

    working_dir = Path(working_dir)
    # working_dir.mkdir(exist_ok=True)
    repo_path = working_dir / repo_name

    # Initialize ClepsSSHWrapper
    client = ClepsSSHWrapper("cleps.inria.fr", username=username)
    client.exec_cmd(f"mkdir -p {working_dir}")

    try:
        # Clone the repository
        client.clone_repo(repo_addr=repo_addr, dst_dir=repo_path)

        # Define Slurm options
        slurm_options = SlurmOptions(
            job_name=f"{repo_name}-job",
            output=f"{working_dir}/outputs"
        )
        sbatch_options = SbatchHeader()

        client.send_job(
            run_cmd=script,
            working_dir=repo_path,
            slurm_options=slurm_options,
            sbatch_options=sbatch_options,
            env_cmd=env_cmd
        )
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
