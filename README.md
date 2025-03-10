# pycleps
A python wrapper for sending jobs to Inria's cluster Cleps.

Automate sending your simulations and getting the outputs. 

## Setup

Run `pip install .`

## Run

```
pycleps [-h] [--username USERNAME] --repo REPO [--wd WD] --script SCRIPT [--env ENV]
               [--cpus-per-task CPUS_PER_TASK] [--wait]
```

You can run your simulations located either on Github or on your local machine.

- If on Github, specify the https web URL (yet, SSH is not configured for pycleps). Otherwise, specify the path of the repository within your environment.
- `--wd` is the working directory where pycleps will clone your repo
- `--script` is the script that will be used to run your experiment
- `--env` is the command that will be used to put you in the right environment for your experiment
- `--wait` will not exit the program until your simulation is not done
