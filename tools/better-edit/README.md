# Better Edit

Apply a batch of exact-string edits across one or more files in **one** call.

Editing was the last hot path still paying one round trip per operation — N
edits meant N calls, each re-sending the whole accumulated context. This
collapses a multi-file change into a single call.

```bash
echo '[{"path":"a.py","old":"foo","new":"bar"}]' | python3 tools/better-edit/better_edit.py
python3 tools/better-edit/better_edit.py '[{"path":"a.py","old":"foo","new":"bar"},{"path":"b.py","old":"x","new":"y"}]'
```

Each edit is `{"path", "old", "new", "replace_all"?}` — `old` must be unique
in the file's current content unless `replace_all` is set, matching a
single-file edit tool's safety rule. Edits to the same path apply in the
given order, each against the previous edit's result.

**All-or-nothing:** every edit is validated against its file's current (or
already-staged) content before anything is written. If any edit in the
batch fails, no file in the batch is written.

Returns line numbers and occurrence counts only — never file content, so
output is bounded regardless of edit size.
