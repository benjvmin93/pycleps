from helpers import SlurmOptions, SbatchHeader
import sys

import paramiko
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

    def clone_repo(self, repo_addr: str | Path, dst_dir: Path = "~/") -> None:
        """Clone repository from github or transfer it from your machine to the cluster."""
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
            self.exec_cmd(f"mkdir -p {dst_dir}")
            with SCPClient(self.client.get_transport()) as scp:
                scp.put(Path(repo_addr), recursive=True, remote_path=dst_dir)
            print(f"Repository copied from local machine as {dst_dir}")

    def send_job(self, run_cmd: str, working_dir: Path, slurm_options: SlurmOptions, sbatch_options: SbatchHeader, env_cmd: str | None = None) -> None:
        """Schedule a job that will run your script on the cluster."""
        slurm_script_path = working_dir / "slurm_job.sbatch"
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
        out = self.exec_cmd(cmd)
        print(out)
        splitted = out.split(' ')   # Extracts job ID and returns it
        jobId = splitted[-1].strip(" \n")
        return jobId

    def wait(self, jobId: str) -> None:
        print(f"Waiting for job {jobId}...")
        while True:
            out = self.exec_cmd(f"scontrol show job {jobId}")
            m = re.search(r"JobState=(\w+)", out)
            state = ""
            if m:
                state = m.group(1)
            else:
                raise Exception("Error while parsing scontrol output {out}")
            print(f"\t{state}")
            if state != "RUNNING":
                break
            time.sleep(10)

        outputs = self.exec_cmd(f"cat outputs/*{jobId}*")
        print(outputs)
        

            
            
