class SlurmOptions:
    """A helper class to generate SLURM configuration directives."""

    def __init__(
        self,
        array: bool = False,
        job_name: str = "",
        time: str = "",
        partition: str = "",
        nodes: int = 1,
        ntasks_per_node: int = 1,
        cpus_per_task: int = 1,
        memory: str = "",
        output: str = "",
        error: str = "",
        other_options: dict[str, str] = {},
    ):
        """
        Initialize SLURM options.

        Args:
            job_name: Name of the SLURM job.
            time: Max wall-clock time (e.g., "01:00:00" for 1 hour).
            partition: SLURM partition to use.
            nodes: Number of nodes to request (default: 1).
            ntasks_per_node: Number of tasks per node (default: 1).
            cpus_per_task: Number of CPUs per task (default: 1).
            memory: Memory per node (e.g., "4G").
            output: File to write standard output (e.g., "job_output.txt").
            error: File to write standard error (e.g., "job_error.txt").
            other_options: Additional SLURM options as key-value pairs.
        """
        self.job_name = job_name
        self.time = time
        self.partition = partition
        self.nodes = nodes
        self.ntasks_per_node = ntasks_per_node
        self.cpus_per_task = cpus_per_task
        self.memory = memory
        self.array = array
        if array:
            output = output / "%A_%a.log"
        else:
            output = output / "%j.log"
        self.output = output
        self.error = error
        self.other_options = other_options or {}

    def to_slurm_directives(self) -> str:
        """Generate SLURM directives as a string."""
        output_suff = "%j.log" if not self.array else "%A_%a.log"
        options_dict = {
            "job-name": self.job_name,
            "time": self.time,
            "partition": self.partition,
            "nodes": self.nodes,
            "ntasks-per-node": self.ntasks_per_node,
            "cpus-per-task": self.cpus_per_task,
            "mem": self.memory,
            "output": f"{self.output}" if self.output != "" else f"{output_suff}",
            "error": self.error,
        }
        options_dict.update(self.other_options)
        directives = [
            f"#SBATCH --{key}={value}"
            for key, value in options_dict.items()
            if value != "" and value is not None
        ]
        return "\n".join(directives)


class SbatchHeader:
    """A helper class to generate sbatch command-line options."""

    def __init__(
        self,
        array: list[int] | list[float],
        account: str = "",
        qos: str = None,
        dependency: str = "",
        mail_user: str = "",
        mail_type: str = None,
        wait: bool = False,
        other_options: dict[str, str] = None,
    ):
        """
        Initialize sbatch command-line options.

        Args:
            account: Account name to charge (e.g., "project_account").
            qos: Quality of service (e.g., "normal", "high").
            dependency: Job dependencies (e.g., "afterok:<job_id>").
            mail_user: Email address to send notifications.
            mail_type: Notification types (e.g., "BEGIN,END,FAIL").
            other_options: Additional sbatch options as key-value pairs.
        """
        self.array = array
        self.account = account
        self.qos = qos
        self.dependency = dependency
        self.mail_user = mail_user
        self.mail_type = mail_type
        self.wait = wait
        self.other_options = other_options or {}

    def __str__(self) -> str:
        return self.to_sbatch_options()

    def to_sbatch_options(self) -> str:
        """Generate sbatch command-line options as a string."""
        options = []
        if self.array:
            options.append(f"--array={','.join([str(x) for x in self.array])}")
        if self.account:
            options.append(f"--account={self.account}")
        if self.qos:
            options.append(f"--qos={self.qos}")
        if self.dependency:
            options.append(f"--dependency={self.dependency}")
        if self.mail_user:
            options.append(f"--mail-user={self.mail_user}")
        if self.mail_type:
            options.append(f"--mail-type={self.mail_type}")
        if self.wait:
            options.append("--wait")
        for key, value in self.other_options.items():
            options.append(f"--{key}={value}")
        return " ".join(options)
