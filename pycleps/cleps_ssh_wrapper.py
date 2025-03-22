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

# argcomplete

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(filename='pycleps.log', encoding='utf-8', level=logging.DEBUG)

class ClepsSSHWrapper:
    def __init__(self, hostname: str, wd: Path, username: str | None = None, password: str | None = None):
        """
        Init an SSH client connected to the given host.
        Authenticate using your SSH key added to the SSH agent.
        Additionally, creates the working directory within the ssh session.
        """
        if not username:
            username = getuser()
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(hostname=hostname, username=username, password=password, look_for_keys=True)    # Look for your key added to the ssh agent
            logger.info(f"Connected to {hostname}")
        except Exception as e:
            logger.exception(e)
            raise Exception(e)

        self.client = client
        self.username = username
        self.wd = wd

    def exec_cmd(self, cmd: str) -> str:
        """"
        Execute a shell command inside the ssh session.
        Raises Exception if stderr is triggered.
        Returns the return of stdout as a string.
        """
        logger.info(f"Sending command `{cmd}`.")
        _, stdout, stderr = self.client.exec_command(cmd)
        err = stderr.read()
        if err:
            logger.error(err)
            raise Exception(err)

        out = stdout.read()
        logger.info(out)
        return out

    def setup_env(self, env_install_cmd: str, repo_path: Path, env_name: str, env_file: Path = None) -> None:
        """
        Create a conda environment regarding the environment file path (ie. .yml file generated by conda).
        If no env_file is passed, then the program uses a default environment and tries to run the envrionment installation command (ie. pip install, cargo build...).
        """
        logger.info(f"Setting up environment from {env_file}")

        if env_file:    # If env file path provided
            with SCPClient(self.client.get_transport()) as scp:
                scp.put(env_file, remote_path=repo_path)

            logger.info(f"Creating conda environment {env_name} with file {env_file}")
            out = self.exec_cmd(f"conda env create -n {env_name} -f {env_file} -y") # Creates a new environment and erases the one with the same name if it exists
            logger.info(out)
            self.exec_cmd(f"conda activate {env_name}")

        # Install project dependencies.
        out = self.exec_cmd(f"cd {repo_path} && {env_install_cmd}")
        logger.info(out)

    def clone_repo(self, repo_addr: str | Path, dst_dir: Path = "~/", git_branch: str = None) -> None:
        """Clone repository from github or transfer it from your machine to the cluster"""
        self.exec_cmd(f"mkdir -p {self.wd}")  # Creates working directory if doesn't exist
        if repo_addr.startswith("git@github.com") or repo_addr.startswith("https://"):  # Clone repo from github
            repo_name = repo_addr.split("/")[-1].replace(".git", "")
            cmd = f"git clone {repo_addr} {dst_dir}"
            try:
                out = self.exec_cmd(cmd)
                logger.info(out)
            except Exception as e:  # Eventually, the repo already exists in the cluster machine
                logger.exception(e)
        else:   # Transfer the repo from local machine
            logger.info(f"Copying local repo {repo_addr} as {dst_dir}")
            with SCPClient(self.client.get_transport()) as scp:
                scp.put(Path(repo_addr), recursive=True, remote_path=dst_dir)

        # Checkout if needed
        if git_branch:
            out = self.exec_cmd(f"git -C {dst_dir} checkout {git_branch}")
            logger.info(out)

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
        logger.debug(cmd)
        out = self.exec_cmd(cmd)
        logger.info(out)
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