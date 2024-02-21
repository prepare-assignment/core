# Prepare assignment

Prepare assignment is a GitHub Actions inspired helper tool to prepare assignments at Fontys Venlo. The goal is to define jobs inside the `prepare.yml` that indicate how to convert a solution project into a student project.

## Dependencies

- Git
- Python >=3.8

## Installation

Prepare-assignment is available from [PyPI](https://pypi.org/).


```bash
# To install:
python3 -m pip install prepare-assignment

# To upgrade
python3 -m pip install --upgrade prepare-assignment
```

## Executing prepare-assignment

To execute a `prepare.yml` simply run `prepare run` from the same directory.

### Command line interface

Use `prepare --help` to which commands and flags are available.

## Example `prepare.yml`

First we need to have tasks available that can be executed. Take for example a look at the [remove](https://github.com/prepare-assignment/remove) task.

The tests use a [testproject](https://github.com/prepare-assignment/core/tree/tests/testproject), which contains an example of a `prepare.yml`, see below for convenience.

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

## Tasks

There are three different kind of tasks available:

- Run tasks: these execute a shell command (for now only bash is supported)
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
    - outputs: the outputs that get set by the task
3. Validate that the task definition is correct against the [json schema](https://github.com/prepare-assignment/core/blob/main/prepare_assignment/schemas/task.schema.json)
4. If python task, create a script that implements desired functionality

