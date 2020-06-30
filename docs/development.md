# Development

### Set-up 

See [Development](../README.md#local-development) instructions.


### Data import
...


### Workflow

#### Before commiting

[Pre-commit hooks](https://pre-commit.com) are responsible for automatically running black, mypy,
etc. on the staged files, before each commit. If there are issues, committing is aborted.

The pre-commit configuration is in the [.pre-commit-config.yaml](../.pre-commit-config.yaml) file.

In case of emergency, it is possible to 
[disable one or more hooks](https://pre-commit.com/#temporarily-disabling-hooks). To completely 
disable all the hooks, run `pre-commit uninstall`.

You can also execute the `test.sh` script: it runs mypy, black, tests, eslint, and stylelint on the
entire project.


#### Git workflow

- rebase, don't merge
- branches overview: master, develop, other branches stemming from develop
- other conventions
