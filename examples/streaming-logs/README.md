# Streaming logs

This has a long-running job that prints out logs using [rich][rich].
Once the jobs is submitted, you can view the logs with `kbatch job logs show <job-id>`.

```python
$ kbatch job submit -f script.sh --name=streaming-logs --image=python:slim --command='["sh", "script.sh"]'
```


[rich]: https://rich.readthedocs.io/
