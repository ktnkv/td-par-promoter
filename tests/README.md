# tests

Python that runs inside a live TouchDesigner, against the Promote tool at `/tools/promote`. No pytest.

Run it from any Python call in TouchDesigner (the project folder must be this repository):

```python
exec(open(project.folder + '/tests/run_tests.py').read())
```

To run a subset, set `ONLY` to part of a test name first: `ONLY = 'unpromote'`.

Each test gets a fresh scratch COMP, `/promote_test_scratch`, and it is destroyed afterwards, pass or fail. Nothing else is created or removed. Update tests call `_update_comps` on the scratch COMPs only, because `Updateall` walks the whole project. The hook tests only read what is installed in `/ui`.

The tests push Promote, Unpromote and Update steps onto the project's undo stack.

| File | Covers |
| --- | --- |
| `test_promote.py` | names, binds, values, headers, groups and axes, refusals |
| `test_unpromote.py` | what is deleted, what stays, refusals |
| `test_update.py` | rename to the current path, signal-flow order, orphans |
| `test_undo.py` | undo and redo of Promote |
| `test_hooks.py` | installed drop hooks, timeline and crumb drop entry points |
