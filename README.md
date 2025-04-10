# pycleps

![ChatGPT Image Apr 10, 2025, 10_54_05 AM](https://github.com/user-attachments/assets/1f665a42-23eb-49ce-854a-ef7bd9cddf70)

A python wrapper for sending jobs to Inria's cluster Cleps.

Automate sending your simulations and getting the outputs. 

## Setup

Run `pip install .`

## Run

```
Usage: pycleps [OPTIONS] COMMAND [ARGS]...

Commands:
    submit: submit a job to Cleps with custom options.
    fetch: download result output(s) of a specific job.

- submit:
    --repo                   TEXT  Repository address (e.g., git@github.com:user/repo.git) [default: None] [required]
    --branch                 TEXT  Repository branch you want to use [default: None]
    --user                   TEXT  Your Cleps username [default: None]
    --wd                     TEXT  Working directory where the git repo will be copied [default]
    --script                 TEXT  Command to run your script [default: None]
    --env                    TEXT  Path of the conda environment .yml file [default: None]    
    --name                   TEXT  Name of the environment inside the cluster [default: pycleps-env]
    --setup                  TEXT  Command to install required packages [default: None]
    --cpt                    TEXT  Number of CPUs required for simulations
    --wait      --no-wait          Wait for job completion before exiting [default: no-wait]
    --array                  TEXT  Parameters for parallel experiments (list or range) [default: None]
    --time                   TEXT  Time limit for simulations
    --help                         Show this message and exit.

- fetch:
    --user                   TEXT  Your Cleps username [default: None]
    --repo                   TEXT  Repository address (e.g., git@github.com:user/repo.git) [default: None] [required]
    --job_id                 TEXT  Job ID to fetch results for [default: None] [required]    
```

Argument completion is implemented on Pycleps. You can try using it for giving the repository branch (locally specified) using `--branch <TAB>`.

You can run your simulations located either on Github or on your local machine.

- If on Github, specify the https web URL (yet, SSH is not configured for pycleps). Otherwise, specify the path of the repository within your environment.
- `--wd` is the working directory where pycleps will clone your repo
- `--script` is the script that will be used to run your experiment
- `--env` is the command that will be used to put you in the right environment for your experiment
- `--wait` will not exit the program until your simulation is not done. If this flag is set, pycleps will automatically fetch your experiment's results when they are done.
- `--array` is an options to specify different parameters for your experiments. It will create multiple tasks with these different arguments. Can either be a range a-b or a list form 1,2,3,4,... These experiments will be ran in parallel on the cluster if ressources are available.
- `--time` is the time limit for running your simulations. 
