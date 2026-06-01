# health-reporter

Responsibilities:

```text
Collect local health
Map raw health to platform whitelist
Scan forbidden business fields
Send only desensitized payloads to platform
```

Allowed platform payload fields:

```text
tenant_id
agent_id
agent_version
status
last_heartbeat
task_pending_count
task_running_count
task_failed_count
error_code
cpu_usage
memory_usage
disk_usage
```
