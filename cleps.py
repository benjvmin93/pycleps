from helpers import SlurmOptions, SbatchHeader

import paramiko
from getpass import getuser, getpass
from pathlib import Path
from scp import SCPClient
import io

class ClepsSSHWrapper:
    def __init__(self, hostname: str, username: str | None = None, public_key: str = None):
        """Init an SSH client connected to the given host"""
        if not username:
            username = getuser()
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        password = getpass("Enter your Cleps password: ")
        client.connect(hostname=hostname, username=username, password=password)
        self.client = client
        self.username = username

    def clone_repo(self, repo_addr: str | Path, dst_dir: Path = "~/") -> None:
        """Clone repository from github or transfer it from your machine to the cluster."""
        if repo_addr.startswith("git@github.com") or repo_addr.startswith("https://"):  # Clone repo from github
            print("Cloning repository from Github...")
            cmd = f"git clone {repo_addr} {dst_dir}"
            self.client.exec_command(cmd)
        else:   # Transfer the repo from local machine
            print(f"Copying {repo_addr} to {dst_dir}")
            self.client.exec_command(f"mkdir -p {dst_dir}")
            with SCPClient(self.client.get_transport()) as scp:
                scp.put(Path(repo_addr), recursive=True, remote_path=dst_dir)

    def send_job(self, run_cmd: str, working_dir: Path, slurm_options: SlurmOptions, sbatch_options: SbatchHeader, env_cmd: str | None = None) -> None:
        """Schedule a job that will run your script on the cluster."""
        slurm_script_path = working_dir / "slurm_job.batch"
        slurm_directives = slurm_options.to_slurm_directives()
        slurm_script = f"""#!/bin/bash

{slurm_directives}

source ~/.bashrc
{env_cmd if env_cmd is not None else ""}

{run_cmd}
"""
        with SCPClient(self.client.get_transport()) as scp:
            scp.putfo(
                io.StringIO(slurm_script), slurm_script_path
            )

        cmd = f"sbatch {sbatch_options} {slurm_script_path}"
        _, stdout, stderr = self.client.exec_command(cmd)
        job_submission_err = stderr.read().decode()
        job_submission_out = stdout.read().decode()
        if job_submission_err != "":
            print(job_submission_err)
            return
        else:
            print(job_submission_out)
        
