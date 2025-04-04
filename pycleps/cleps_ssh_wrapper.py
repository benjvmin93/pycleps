from pycleps.helpers import SlurmOptions, SbatchHeader

import paramiko
from getpass import getuser
from pathlib import Path
from scp import SCPClient
import io
import re

import logging

logger = logging.getLogger(__name__)


class ClepsSSHWrapper:
    def __init__(
        self, wd: Path, username: str | None = None, password: str | None = None
    ):
        """
        Init an SSH client connected to the given host.
        Authenticate using your SSH key added to the SSH agent.
        Additionally, creates the working directory within the ssh session.
        """
        if not username:
            username = getuser()

        self.username = username
        self.wd = wd

        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.client.connect(
            hostname="cleps.inria.fr",
            username=self.username,
            password=password,
            look_for_keys=True,
        )  # Look for your key added to the ssh agent

    def exec_cmd(self, cmd: str) -> str:
        """
        Execute a shell command inside the ssh session.
        Raises Exception if stderr is triggered.
        Returns the return of stdout as a string.
        """
        logger.debug(f"Sending command `{cmd}`.")
        _, stdout, stderr = self.client.exec_command(cmd)
        err = stderr.read()
        if err:
            if isinstance(err, str):
                logger.error(err)
                raise Exception(err)
            else:
                err = err.decode()

        out = stdout.read()
        if not isinstance(err, str):
            out = out.decode()

        logger.info(out)
        return out

    def setup_env(
        self,
        env_install_cmd: str,
        repo_path: Path,
        env_name: str,
        env_file: Path = None,
    ) -> None:
        """
        Create a conda environment regarding the environment file path (ie. .yml file generated by conda).
        If no env_file is passed, then the program uses a default environment and tries to run the envrionment installation command (ie. pip install, cargo build...).
        """
        if env_file:  # If env file path provided
            env_file = Path(env_file)
            new_env_file_path = repo_path / env_file.name
            logger.info(
                f"Environment file passed. Copying {env_file} to {new_env_file_path}"
            )
            with SCPClient(self.client.get_transport()) as scp:
                scp.put(env_file, remote_path=new_env_file_path)

            logger.info(
                f"Creating conda environment {env_name} with file {new_env_file_path}"
            )
            print("Setting up your environment.")
            out = self.exec_cmd(
                f"conda env create -n {env_name} -f {new_env_file_path} -y"
            )  # Creates a new environment and erases the one with the same name if it exists
            print(out)

        # Install project dependencies.
        try:
            out = self.exec_cmd(
                f"cd {repo_path} && conda activate {env_name} && {env_install_cmd}"
            )
            print(out)
        except Exception as e:
            print(e)

    def clone_repo(
        self, repo_addr: str | Path, dst_dir: Path = None, git_branch: str = None
    ) -> None:
        """Clone repository from github or transfer it from your machine to the cluster. If the repo already exists on the remote machine, does nothing."""
        self.exec_cmd(
            f"mkdir -p {self.wd}"
        )  # Creates working directory if doesn't exist
        if (
            repo_addr.startswith("git@github.com") or repo_addr.startswith("https://")
        ) and repo_addr.endswith(".git"):  # Clone repo from github
            repo_name = repo_addr.split("/")[-1].replace(".git", "")
            if dst_dir is None:
                dst_dir = self.wd / repo_name
            logger.info(self.exec_cmd(f"git clone {repo_addr} {dst_dir}"))
        else:  # Transfer the repo from local machine
            repo_addr = Path(repo_addr)
            if dst_dir is None:
                dst_dir = self.wd / repo_addr.name

            if not repo_addr.exists():
                err_msg = f"The path `{repo_addr}` does not exist on your local machine"
                logger.error(err_msg)
                raise Exception(err_msg)

            logger.info(f"Copying local repo {repo_addr} as {dst_dir}")
            if not isinstance(repo_addr, Path):
                repo_addr = Path(repo_addr)
            with SCPClient(self.client.get_transport()) as scp:
                scp.put(repo_addr, recursive=True, remote_path=dst_dir)

        # Checkout if needed
        if git_branch is not None:
            self.exec_cmd(f"git -C {dst_dir} checkout {git_branch}")
            logger.info(f"Successfully checkout into {git_branch}")

    def send_job(
        self,
        run_cmd: str,
        working_dir: Path,
        slurm_options: SlurmOptions,
        sbatch_options: SbatchHeader,
        env_name: str,
    ) -> str:
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
            scp.putfo(io.StringIO(slurm_script), slurm_script_path)
        cmd = f"sbatch {sbatch_options} {slurm_script_path}"
        logger.debug(cmd)
        out = self.exec_cmd(cmd)
        logger.info(out)
        splitted = out.split(" ")  # Extracts job ID and returns it
        jobId = splitted[-1].strip(" \n")
        return jobId

    def fetch(self, jobId: str, remote_path: Path) -> tuple[Path, str] | list[tuple[Path, str]]:
        """
        Copy the output(s) of a job given by its id and the remote path in which the outputs are stored on the local machine.
        Returns the paths and outputs of the one or multiple jobs as a string or list of strings.
        """
        sftp_cli = self.client.open_sftp()
        out = sftp_cli.listdir(str(remote_path / "outputs"))
        files = [f"{remote_path}/outputs/{n}" for n in out if jobId in n]
        logger.info(f"Fetching {len(files)} files")

        output_path = Path("./outputs/")
        output_path.mkdir(exist_ok=True)

        fetched = []

        for file in files:
            local_file_path = output_path / Path(file).name

            sftp_cli.get(file, str(local_file_path))  

            with open(local_file_path, "r", encoding="utf-8") as f:
                content = f.read()
                fetched.append((local_file_path, content))

        sftp_cli.close()

        return fetched if len(fetched) > 1 else fetched[0]

    def get_output(self, repo_path: Path, jobId: str) -> list[tuple[str, Path]]:
        """Get the stdout paths of each scheduled tasks according to the job id. Used when we waited for the job to complete."""
        out = self.exec_cmd(f"scontrol show job {jobId}")

        # Use regex to find all ArrayTaskId and StdOut pairs
        task_info = re.findall(r"ArrayTaskId=(\d+).*?StdOut=(\S+)", out, re.DOTALL)
        if not task_info:
            # If no ArrayTaskId is found, fall back to single JobId and StdOut
            task_info = re.findall(r"JobId=(\d+).*?StdOut=(\S+)", out, re.DOTALL)

        if not task_info:
            raise Exception(f"Error parsing scontrol output: {out}")

        return [(id, path) for id, path in task_info]  # List of (id, stdout_path)

    def fetch_outputs(
        self, jobs: list[tuple[str, Path]], local_path: Path = "."
    ) -> None:
        print(f"Attempting to fetch {len(jobs)} results...")
        file_paths = []
        with SCPClient(self.client.get_transport()) as scp:
            for job, path in jobs:
                scp.get(path, local_path)
                file_paths.append(path)

        print(f"{len(file_paths)} files have been successfully fetched:\n")
        print("\n\t".join(file_paths))
