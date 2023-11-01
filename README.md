# Prepare assignment

Prepare assignment is a GitHub Actions inspired helper tool to prepare assignments at Fontys Venlo. The goal is to define steps inside the `prepare.yml` that indicate how to convert a solution project into a student project.

## Dependencies

- Git
- Python >=3.8

## Example

First we need to have actions available that can be executed. Take for example a look at the [remove](https://github.com/prepare-assignment/remove) action.

The tests use a [testproject](https://github.com/prepare-assignment/core/tree/tests/testproject), which contain an example of a `prepare.yml`, see below for convenience.

```yaml
name: Test project
steps:
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
      run: echo '${{ steps.codestripper.outputs.stripped-files }}' > out.txt
```

For people familiar with GitHub Actions this should look very familiar. We have steps that indicate what should happen to prepare an assignment. The Actions are defined in their own repositories, if the `uses` tag doesn't have a username/organization, it will default to `prepare-assignment`. So for example the `remove` action uses the following repository: [prepare-assignment/remove](https://github.com/prepare-assignment/remove)

## Actions

There are three different kind of actions available:

- Run actions: these execute a shell command (for now only bash is supported)
- Python actions: these execute a python script
- Composite actions: these combine multiple actions into one

### Custom Actions

It is possible to create custom (python/composite) actions.

1. Create a repository
2. Define the properties of the action in `action.yml`, these include
    - id*: unique identifier
    - name*: name of the action
    - description*: short description
    - runs*: whether it is a python or composite actions
    - inputs: the inputs for the action
    - outputs: the outputs that get set by the action
3. Validate that the action definition is correct against the [json schema](https://github.com/prepare-assignment/core/blob/main/prepare_assignment/schemas/action.schema.json)
4. If python action, create a script that implements desired functionality

