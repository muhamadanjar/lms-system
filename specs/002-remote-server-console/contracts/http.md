# HTTP Contract: Remote Server Inventory

REST surface for the inventory. Base prefix: `/api/v1/servers`. All endpoints require a
bearer JWT (`Authorization: Bearer <jwt>`) validated against User Management; permission
checks use the permissions returned by `auth_info`.

## Permission mapping

| Endpoint | Required permission |
| --- | --- |
| `GET /api/v1/servers` · `GET /api/v1/servers/{id}` | `servers.view` |
| `POST /api/v1/servers` | `servers.create` |
| `PATCH /api/v1/servers/{id}` | `servers.update` |
| `DELETE /api/v1/servers/{id}` | `servers.delete` |

## `GET /api/v1/servers`

Query: `page`, `page_size` (default 25, max 100), `q` (matches name/host).

```jsonc
// 200
{
  "items": [
    {
      "id": "3f0e...",
      "name": "prod-api-01",
      "host": "10.0.0.21",
      "port": 22,
      "username": "deploy",
      "access_method": "PUBLIC_KEY",
      "has_credential": true,
      "passphrase_protected": false,
      "host_key": "one-host-key-fingerprint...",   // truncated fingerprint or null
      "created_at": "2026-09-23T…Z",
      "updated_at": "2026-09-23T…Z"
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 25
}
```

**Never** contains `credential_ciphertext` / `credential_nonce` / key material in any
field — neither list nor detail responses.

## `POST /api/v1/servers`

```jsonc
{
  "name": "prod-api-01",
  "host": "10.0.0.21",
  "port": 22,
  "username": "deploy",
  "access_method": "PUBLIC_KEY",
  "credential": {                  // secret, transport-only
    "value": "-----BEGIN ... PRIVATE KEY-----\n...",  // or password string
    "passphrase": "optional-passphrase"
  }
}
```

Responses:

```jsonc
// 201 — same shape as list item; credential fields absent
{ "id": "3f0e...", "name": "prod-api-01", "has_credential": true, ... }
```

Errors (existing exception-handling conventions):
- `422` — validation (empty name, bad port, raw secret present, passphrase without key).
- `401` / `403` — missing permission or invalid token.
- `409` — duplicate `name`.

## `PATCH /api/v1/servers/{id}`

All fields optional; secrets are **only** updated when `credential` is explicitly present.
Omitting `credential` keeps the existing encrypted blob.

```jsonc
{ "name": "prod-api-01-v2", "port": 2222, "credential": { "value": "new-secret" } }
```

Response is the updated item shape. `200`.

## `DELETE /api/v1/servers/{id}`

Soft delete (`deleted_at` set). If a console is active, it is closed
(`closed{reason:"server_deleted"}`) and the registry entry freed. `204`.

## Error body convention

```jsonc
{ "detail": "Human-readable failure", "error_code": "<code>" }
```

No secret material ever appears in error payloads (spec US4).