# pycleps
A python wrapper for sending jobs to Inria's cluster Cleps.

Automate sending your simulations and getting the outputs. 

## Setup

Run `pip install .`

## Run

```
pycleps [-h] [--username USERNAME] --repo REPO [--wd WD] --script SCRIPT [--env ENV]
               [--cpus-per-task CPUS_PER_TASK] [--wait] [--array ARRAY] [--time TIME]
```

Argument completion is implemented on Pycleps. You can try using it for giving the repository branch (locally specified) using `--branch <TAB>`.

You can run your simulations located either on Github or on your local machine.

- If on Github, specify the https web URL (yet, SSH is not configured for pycleps). Otherwise, specify the path of the repository within your environment.
- `--wd` is the working directory where pycleps will clone your repo
- `--script` is the script that will be used to run your experiment
- `--env` is the command that will be used to put you in the right environment for your experiment
- `--wait` will not exit the program until your simulation is not done. If this flag is set, pycleps will automatically fetch your experiment's results when they are done.
- `--array` is an options to specify different parameters for your experiments. It will create multiple tasks with these different arguments. Can either be a range a-b or a list form 1,2,3,4,...
- `--time` is the time limit for running your simulations. 