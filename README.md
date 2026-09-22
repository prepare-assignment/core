# Prepare assignment

Prepare assignment is a GitHub Actions inspired helper tool to prepare assignments at Fontys Venlo. The goal is to define jobs inside the `prepare.yml` that indicate how to convert a solution project into a student project.

## Dependencies

- Git
- Python >=3.11

## Installation

Prepare-assignment is available from [PyPI](https://pypi.org/project/prepare-assignment/).


```bash
# To install:
python3 -m pip install prepare-assignment

# To upgrade
python3 -m pip install --upgrade prepare-assignment
```

## Executing prepare-assignment

To execute a `prepare.yml` simply run `prepare run` from the same directory.

### Command line interface

Use `prepare --help` to see which commands and flags are available.

## Example `prepare.yml`

First we need to have tasks available that can be executed. Take for example a look at the [remove](https://github.com/prepare-assignment/remove) task.

The tests use a [testproject](https://github.com/prepare-assignment/core/tree/main/tests/testproject), which contains an example of a `prepare.yml`, see below for convenience.

```yaml
name: Test project
jobs:
  prepare:
    - name: remove out
      uses: remove
      with:
        input:
          - "out"
          - "out.txt"
        force: true
        recursive: true
    - name: codestripper
      id: codestripper
      uses: codestripper
      with:
        include:
          - "**/*.java"
          - "pom.xml"
        working-directory: "solution"
        verbosity: 5
    - name: Test a run command with substitution
      run: echo '${{ tasks.codestripper.outputs.stripped-files }}' > out.txt
```

For people familiar with GitHub Actions this should look very familiar. We have jobs that indicate what should happen to prepare an assignment. The tasks are defined in their own repositories, if the `uses` tag doesn't have a username/organization, it will default to `prepare-assignment`. So for example the `remove` task uses the following repository: [prepare-assignment/remove](https://github.com/prepare-assignment/remove)

## Step reference

Every step has a `name` and either `uses` (a task) or `run` (a shell command).

| Property            | Applies to     | Description                                                                                                |
|---------------------|----------------|------------------------------------------------------------------------------------------------------------|
| `name`              | all            | Name of the step (required)                                                                                |
| `id`                | all            | Identifier used to reference the outputs of the step: `${{ tasks.<id>.outputs.<name> }}`                   |
| `if`                | all            | Only run the step if the expression is true, see [Conditions](#conditions)                                 |
| `uses`              | task           | The task to execute, e.g. `remove`, `remove@v1`, `my-org/my-task@v1.2.0`                                   |
| `with`              | task           | The inputs of the task                                                                                     |
| `run`               | run            | The command (script) to execute                                                                            |
| `shell`             | run            | `bash` (default), `sh`, `pwsh`, `powershell`, `cmd` or `python`                                            |
| `working-directory` | all            | Directory (relative to the `prepare.yml`) in which the step is executed                                    |
| `env`               | all            | Environment variables for this step only, values can contain expressions                                   |
| `continue-on-error` | all            | If `true`, a failure of this step doesn't fail the job                                                     |

The default shell can be changed in the [config file](#config-file). Using `shell: python` is the most portable
option, as Python is always available.

Like GitHub Actions, the script is written to a temporary file and executed as:

| Shell        | Command                                                         | Behaviour                                                        |
|--------------|-----------------------------------------------------------------|------------------------------------------------------------------|
| `bash`       | `bash --noprofile --norc -eo pipefail <file>`                   | Stops at the first failing command (also inside a pipe)          |
| `sh`         | `sh -e <file>`                                                  | Stops at the first failing command                               |
| `pwsh`       | `pwsh -NoProfile -NonInteractive -Command ". '<file>'"`         | Stops at the first error, fails if the last program failed       |
| `powershell` | `powershell -NoProfile -NonInteractive -Command ". '<file>'"`   | Same as `pwsh` (Windows PowerShell 5.1)                          |
| `cmd`        | `cmd /D /E:ON /V:OFF /S /C "CALL "<file>""`                     | Doesn't stop on errors, the exit code of the last command counts |
| `python`     | `python <file>`                                                 | The Python interpreter that runs prepare                         |

```yaml
- name: Create checksum
  shell: python
  working-directory: out/assignment
  run: |
    import hashlib
    digest = hashlib.sha256(open("pom.xml", "rb").read()).hexdigest()
    open("pom.xml.sha256", "w").write(f"{digest}  pom.xml\n")
```

### Expressions

Values can contain expressions: `${{ <expression> }}`. The following contexts are available:

- `inputs.<name>`: the inputs of a composite task
- `env.<NAME>`: environment variables (an unset variable is empty)
- `tasks.<id>.outputs.<name>`: the outputs of a previous step

Referencing something that doesn't exist (e.g. a typo like `inputs.nmae`) fails the step, instead of silently
evaluating to an empty string. The operators `==`, `!=`, `<`, `>`, `&&`, `||` and `!` and the functions
`contains`, `startsWith` and `endsWith` are supported.

### Conditions

Just like GitHub Actions, a step is skipped when a previous step failed, unless its `if` uses one of the status
functions `success()`, `failure()` or `always()`. So `if: inputs.clean` behaves as `success() && inputs.clean`.

```yaml
- name: Clean up (also when something failed)
  if: always()
  uses: remove
  with:
    input: ["out"]
    force: true
    recursive: true
```

## Checking for updates

`prepare check` shows which of the tasks used in the `prepare.yml` have newer versions (use `--all` to check all
installed tasks). Tasks that use a moving version (`latest`, `main` or a prefix like `v1`) can be updated with
`prepare task update <task>`.

## Config file

It is possible to specify global options in a config file. The location of the config file can be found by running `prepare` without any commands.

The following settings are available:

```yml
core:
  git-mode: "ssh|https"
  verbose: int
  debug: int
  shell: "bash|sh|pwsh|powershell|cmd|python" # default shell for run steps (default: bash)
```

## Tasks

There are three different kind of tasks available:

- Run tasks: these execute a shell command (see `shell` below)
- Python tasks: these execute a python script
- Composite tasks: these combine multiple tasks into one

### Custom tasks

It is possible to create custom (python/composite) tasks.

1. Create a repository
2. Define the properties of the task in `task.yml`, these include
    - id*: unique identifier
    - name*: name of the task
    - description*: short description
    - runs*: whether it is a python or composite task
    - inputs: the inputs for the task
    - outputs: the outputs that get set by the task. For composite tasks an output gets its value from an
      expression: `value: ${{ tasks.<id>.outputs.<name> }}`
3. Validate that the task definition is correct against the [json schema](https://github.com/prepare-assignment/core/blob/main/prepare_assignment/schemas/task.schema.json)
4. If python task, create a script that implements desired functionality

## Releases

Releases are automated with [semantic-release](https://semantic-release.gitbook.io/). Pull requests are squash merged, so the PR title becomes the commit on `main` and must follow [Conventional Commits](https://www.conventionalcommits.org/) (checked on every PR):

| PR title | Release |
|----------|---------|
| `fix: ...`, `perf: ...` | patch (1.2.3 → 1.2.4) |
| `feat: ...` | minor (1.2.3 → 1.3.0) |
| `!` after the type (e.g. `feat!: ...`, `refactor!: ...`) or a `BREAKING CHANGE:` footer | major (1.2.3 → 2.0.0) |
| `docs:`, `chore:`, `ci:`, `build:`, `refactor:`, `test:`, `style:`, `revert:` | no release |

On every merge to `main` the next version is determined, tagged (`vX.Y.Z`), a GitHub release is created and the package is published to PyPI. The version is set during the build and is not committed, so the version in `pyproject.toml` is not the released version.
