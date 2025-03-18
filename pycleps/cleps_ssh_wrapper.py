from pycleps.helpers import SlurmOptions, SbatchHeader
import sys

import paramiko
import asyncio
from getpass import getuser, getpass
from pathlib import Path
from scp import SCPClient
import io
import re
import time

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

    def exec_cmd(self, cmd: str) -> str:
        _, stdout, stderr = self.client.exec_command(cmd)

        err = stderr.read().decode()
        if err:
            raise Exception(err)

        return stdout.read().decode()

    def setup_env(self, env_file: Path, env_install_cmd: str) -> str:
        """Create a conda environment regarding the environment file path and returns the name of the environment."""
        # Extract environment name from env file and check if it already exists.
        out = self.exec_cmd(f"cat {env_file}")
        lines = out.splitlines()
        first_line = lines[0]
        name = first_line.split(":")[-1].strip()

        env_names = self.exec_cmd("conda env list")
        env_names = env_names.splitlines()
        exists = False
        for n in env_names:
            if name in n:
                exists = True
                print(f"Found environment {name}.")
                break

        if not exists:
            print(f"Setting up environment from {env_file}...")
            out = self.exec_cmd(f"conda env create -f {env_file}")
            print(out)
        
        # Install project dependencies.
        out = self.exec_cmd(f"conda activate {name}")
        print(out)

        out = self.exec_cmd(env_install_cmd)
        print(out)

        return name

    def clone_repo(self, repo_addr: str | Path, dst_dir: Path = "~/") -> None:
        """Clone repository from github or transfer it from your machine to the cluster"""
        if repo_addr.startswith("git@github.com") or repo_addr.startswith("https://"):  # Clone repo from github
            print("Cloning repository from Github...")
            repo_name = repo_addr.split("/")[-1].replace(".git", "")
            cmd = f"git clone {repo_addr} {dst_dir}"
            try:
                self.exec_cmd(cmd)
                print(f"Repository cloned as {dst_dir}")
            except Exception as e:  # Eventually, the repo already exists in the cluster machine
                print(e)
        else:   # Transfer the repo from local machine
            with SCPClient(self.client.get_transport()) as scp:
                scp.put(Path(repo_addr), recursive=True, remote_path=dst_dir)
            print(f"Repository copied from local machine as {dst_dir}")

    def send_job(self, run_cmd: str, working_dir: Path, slurm_options: SlurmOptions, sbatch_options: SbatchHeader, env_name: str) -> str:
        """Schedule a job that will run your script on the cluster and returns the job ID of your experiment."""
        slurm_script_path = working_dir / "slurm_job.sbatch"
        slurm_directives = slurm_options.to_slurm_directives()
        slurm_script = f"""#!/bin/bash

{slurm_directives}

source ~/.bashrc
conda activate {env_name}

{run_cmd} {"${SLURM_ARRAY_TASK_ID}" if sbatch_options.array else ""}
"""
        with SCPClient(self.client.get_transport()) as scp:
            scp.putfo(
                io.StringIO(slurm_script), slurm_script_path
            )
        cmd = f"sbatch {sbatch_options} {slurm_script_path}"
        out = self.exec_cmd(cmd)
        print(out)
        splitted = out.split(' ')   # Extracts job ID and returns it
        jobId = splitted[-1].strip(" \n")
        return jobId

    def get_output(self, repo_path: Path, jobId: str) -> list[tuple[str, Path]]:
        """Get the stdout paths of each scheduled tasks according to the job id. Used when we waited for the job to complete."""
        out = self.exec_cmd(f"scontrol show job {jobId}")
        ids = []
        
        # Use regex to find all ArrayTaskId and StdOut pairs
        task_info = re.findall(r"ArrayTaskId=(\d+).*?StdOut=(\S+)", out, re.DOTALL)
        if not task_info:
            # If no ArrayTaskId is found, fall back to single JobId and StdOut
            task_info = re.findall(r"JobId=(\d+).*?StdOut=(\S+)", out, re.DOTALL)

        if not task_info:
            raise Exception(f"Error parsing scontrol output: {out}")

        return [(id, path) for id, path in task_info]    # List of (id, stdout_path)

    def fetch_outputs(self, jobs: list[tuple[str, Path]], local_path: Path = '.') -> None:
        print(f"Attempting to fetch {len(jobs)} results...")
        file_paths = []
        with SCPClient(self.client.get_transport()) as scp:
            for job, path in jobs:
                scp.get(path, local_path)
                file_paths.append(path)

        print(f"{len(file_paths)} files have been successfully fetched:\n\t{'/n/t'.join(file_paths)}")