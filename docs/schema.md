# Schema

## `vitality deps --format json`

<!-- deps-json-schema:start -->
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schema_version", "scan_id", "generated_at", "dependencies"],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "1.0"
    },
    "scan_id": {
      "type": "string"
    },
    "generated_at": {
      "type": "string"
    },
    "dependencies": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "declared", "runtime_calls", "status"],
        "properties": {
          "name": {
            "type": "string"
          },
          "declared": {
            "type": "boolean"
          },
          "runtime_calls": {
            "type": "integer",
            "minimum": 0
          },
          "status": {
            "type": "string",
            "enum": ["used", "unused"]
          }
        }
      }
    }
  }
}
```
<!-- deps-json-schema:end -->
