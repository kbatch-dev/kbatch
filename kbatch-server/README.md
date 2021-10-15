# kbatch-server

The server component of kbatch.

## Testing

The `.env.test` file contains settings for unit tests. You should have kubernetes configured independently.

```
$ KBATCH_SETTINGS_PATH=.env.test pytest
```
