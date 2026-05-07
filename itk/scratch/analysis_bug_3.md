# Bug Analysis - PriorityQueue.shutdown() AttributeError

## Log Lines
The error was caught during the execution of the ITK tests. The test runner reported:
```
RuntimeError: JSON-RPC Error: {'code': -32603, 'message': "'PriorityQueue' object has no attribute 'shutdown'"}
```
In the agent logs (`agent_current.log`), the following traceback was found:
```
AttributeError: 'PriorityQueue' object has no attribute 'shutdown'
```

## Description of Applied Fix
The `shutdown()` method on `asyncio.PriorityQueue` is only available in Python 3.13+. The test environment seems to be running an older version of Python.
To fix this, I will add a check to ensure the method exists before calling it:
```python
if hasattr(self._request_queue, 'shutdown'):
    self._request_queue.shutdown(immediate=True)
```
This will be applied in `standalone-itk/src/a2a/server/agent_execution/active_task.py` at lines 297, 534, and 590.
