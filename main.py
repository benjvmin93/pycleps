from cleps import ClepsSSHWrapper
from pathlib import Path
from helpers import SlurmOptions, SbatchHeader

if __name__ == "__main__":
    working_dir = "wd"
    repo_path = Path(working_dir) / "test/"
    script_path = repo_path / "hello.py"

    username = ""   # Replace with your own credentials
    password = ""

    slurm_options = SlurmOptions(
        job_name="hello_test",
        output=f"{working_dir}'/outputs'")
    sbatch_options = SbatchHeader()

    client = ClepsSSHWrapper("cleps.inria.fr", username=username, password=password)

    client.clone_repo(repo_addr="", dst_dir=working_dir)
    client.send_job(run_cmd=f"python {script_path}", working_dir=Path(working_dir), slurm_options=slurm_options, sbatch_options=sbatch_options)