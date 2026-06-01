# Agent API Contract

> Project: V4.1 lawyer-side local Agent data plane  
> Scope: M16 API contract and OpenAPI export  
> Runtime: `services/agent-api/app/main.py` with FastAPI routers

---

## 1. Contract Rules

All Agent API routes keep the MVP response envelope:

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

Errors use the same envelope:

```json
{
  "code": 400,
  "message": "error message",
  "data": null
}
```

Protected routes require `Authorization: Bearer <token>`. `POST /api/agent/auth/login`, `POST /api/agent/auth/logout`, `/`, and `/health` are the only routes that do not require an authenticated local user.

The platform must not receive case names, file names, document text, chunks, vectors, questions, answers, prompts, model API keys, or database credentials.

---

## 2. OpenAPI Export

Export the current schema without starting uvicorn:

```bash
.venv-agent-api/bin/python scripts/export-agent-openapi.py --output docs/agent-api-openapi.json
```

Print to stdout:

```bash
.venv-agent-api/bin/python scripts/export-agent-openapi.py
```

---

## 3. Route Groups

| Group | Method | Path | Auth | Purpose |
|---|---|---|---|---|
| Console | GET | `/` | No | FastAPI migration console page |
| Health | GET | `/health` | No | Local Agent health payload |
| Auth | POST | `/api/agent/auth/login` | No | Local admin login |
| Auth | POST | `/api/agent/auth/logout` | No | Local logout by bearer token |
| Auth | GET | `/api/agent/auth/me` | Yes | Current local user |
| Status | GET | `/api/agent/status` | Yes | Agent status payload |
| Status | GET | `/api/agent/status/dependencies` | Yes | Database, storage, task, vector, model, OCR dependency state |
| Status | POST | `/api/agent/activate` | Yes | Register Agent with platform control plane |
| Status | POST | `/api/agent/report-health` | Yes | Send desensitized health payload to platform |
| Data Sources | POST | `/api/agent/data-sources/check-permission` | Yes | Check local directory permission |
| Data Sources | GET | `/api/agent/data-sources` | Yes | List configured local directories |
| Data Sources | POST | `/api/agent/data-sources` | Yes | Add existing local directory |
| Data Sources | POST | `/api/agent/data-sources/{data_source_id}/scan` | Yes | Scan local directory into a case or knowledge base |
| Knowledge Bases | GET | `/api/agent/knowledge-bases` | Yes | List accessible knowledge bases |
| Knowledge Bases | POST | `/api/agent/knowledge-bases` | Yes | Create a private or team knowledge base |
| Knowledge Bases | GET | `/api/agent/knowledge-bases/{kb_id}` | Yes | Get knowledge base detail |
| Knowledge Bases | PATCH | `/api/agent/knowledge-bases/{kb_id}` | Yes | Update knowledge base metadata and AI flag |
| Knowledge Bases | POST | `/api/agent/knowledge-bases/{kb_id}/review` | Yes | Transition review status with audit trail |
| Knowledge Bases | POST | `/api/agent/knowledge-bases/{kb_id}/archive` | Yes | Archive a knowledge base |
| Knowledge Bases | GET | `/api/agent/knowledge-bases/{kb_id}/tree` | Yes | Get folders and files visible to current user |
| Knowledge Bases | GET | `/api/agent/knowledge-bases/{kb_id}/members` | Yes | List knowledge base members |
| Knowledge Bases | POST | `/api/agent/knowledge-bases/{kb_id}/members` | Yes | Grant or update knowledge base member role |
| Knowledge Bases | POST | `/api/agent/knowledge-bases/{kb_id}/members/{member_id}/revoke` | Yes | Revoke a knowledge base member |
| Knowledge Bases | GET | `/api/agent/knowledge-bases/{kb_id}/stats` | Yes | Get knowledge base file, folder, member, and size stats |
| Folders | POST | `/api/agent/folders` | Yes | Create a folder under a knowledge base |
| Folders | PATCH | `/api/agent/folders/{folder_id}` | Yes | Rename, move, or reorder a folder |
| Folders | DELETE | `/api/agent/folders/{folder_id}` | Yes | Soft delete a folder and its nested files |
| Folders | POST | `/api/agent/folders/{folder_id}/restore` | Yes | Restore a soft-deleted folder |
| Permissions | GET | `/api/agent/permissions/resource` | Yes | List ACL entries for a resource |
| Permissions | GET | `/api/agent/permissions/effective` | Yes | Resolve effective permissions for a resource and user |
| Permissions | POST | `/api/agent/permissions/grant` | Yes | Add or update an allow ACL entry |
| Permissions | POST | `/api/agent/permissions/deny` | Yes | Add or update a deny ACL entry |
| Permissions | POST | `/api/agent/permissions/check` | Yes | Check whether a user can perform an action |
| Permissions | DELETE | `/api/agent/permissions/{entry_id}` | Yes | Delete an ACL entry |
| Tasks | GET | `/api/agent/tasks` | Yes | List processing tasks |
| Tasks | POST | `/api/agent/tasks/run-pending` | Yes | Run pending tasks in process |
| Tasks | GET | `/api/agent/tasks/{task_id}` | Yes | Get task detail |
| Tasks | POST | `/api/agent/tasks/{task_id}/retry` | Yes | Retry failed task |
| Tasks | POST | `/api/agent/worker/run-once` | Yes | Run worker once |
| Cases | GET | `/api/agent/cases` | Yes | List case spaces |
| Cases | POST | `/api/agent/cases` | Yes | Create case space |
| Cases | GET | `/api/agent/cases/{case_id}` | Yes | Get case detail |
| Cases | POST | `/api/agent/cases/summary` | Yes | Create local case summary |
| Files | GET | `/api/agent/files` | Yes | List local files, optionally filtered by case, knowledge base, or folder |
| Files | POST | `/api/agent/files/upload` | Yes | Upload file content to local case or knowledge base storage |
| Files | POST | `/api/agent/files/parse` | Yes | Parse and index local file |
| Files | PATCH | `/api/agent/files/{file_id}` | Yes | Move a file to another folder or root |
| Files | DELETE | `/api/agent/files/{file_id}` | Yes | Soft delete a local file |
| Files | POST | `/api/agent/files/{file_id}/restore` | Yes | Restore a soft-deleted local file |
| Model Configs | GET | `/api/agent/model-configs` | Yes | List local model configs with masked key |
| Model Configs | POST | `/api/agent/model-configs` | Yes | Save local model config |
| Model Configs | GET | `/api/agent/model-configs/{config_id}` | Yes | Get model config with masked key |
| Model Configs | POST | `/api/agent/model-configs/{config_id}/test-chat` | Yes | Test chat model connectivity |
| Model Configs | POST | `/api/agent/model-configs/{config_id}/test-embedding` | Yes | Test embedding model connectivity |
| RAG | POST | `/api/agent/rag/query` | Yes | Ask a case-scoped local RAG question |
| RAG | POST | `/api/agent/rag/retrieve` | Yes | Retrieve case-scoped local chunks |
| Vector Store | POST | `/api/agent/vector-store/sync-qdrant` | Yes | Sync local vectors to local/private Qdrant |
| Chats | GET | `/api/agent/chats` | Yes | List local chat sessions |
| Chats | GET | `/api/agent/chats/{session_id}` | Yes | Get local chat messages |
| Evidences | GET | `/api/agent/evidences` | Yes | List evidence records for a case |
| Evidences | POST | `/api/agent/evidences` | Yes | Create evidence record locally |
| Audit Logs | GET | `/api/agent/audit-logs` | Yes | List local audit logs |

---

## 4. M16 Acceptance

M16 is accepted when:

```text
OpenAPI schema can be exported without starting uvicorn.
All M15 routes appear in the generated schema.
The route contract is documented for frontend, test, and delivery use.
The schema export does not create or open the default Agent database.
```
