# Schema

Este documento versiona o contrato persistido em SQLite e os formatos JSON
expostos pela CLI no MVP.

## SQLite

O banco local fica em `.vitality/data.db` e usa o schema de
`src/vitality/store/schema.sql`.

### `commits`

Uma linha por arquivo alterado em um commit.

| Coluna | Tipo | Nulo | Descricao |
|---|---|---|---|
| `commit_hash` | `TEXT` | nao | Hash do commit. |
| `author` | `TEXT` | nao | Autor do commit como retornado pelo git. |
| `committed_at` | `TEXT` | nao | Timestamp ISO 8601 do commit. |
| `file_path` | `TEXT` | nao | Caminho do arquivo no repositorio. |

Chave primaria: (`commit_hash`, `file_path`).

### `declared_dependencies`

Uma linha por dependencia declarada no manifesto suportado pelo MVP.

| Coluna | Tipo | Nulo | Descricao |
|---|---|---|---|
| `name` | `TEXT` | nao | Nome normalizado da dependencia. |
| `version_spec` | `TEXT` | sim | Especificador de versao, quando declarado. |
| `source_file` | `TEXT` | nao | Arquivo de origem, por exemplo `requirements.txt`. |

Chave primaria: `name`.

### `runtime_calls`

Uma linha por simbolo observado em runtime dentro de um scan.

| Coluna | Tipo | Nulo | Descricao |
|---|---|---|---|
| `symbol` | `TEXT` | nao | Nome do modulo, dependencia ou funcao qualificada. |
| `call_count` | `INTEGER` | nao | Quantidade de chamadas observadas. Padrao: `0`. |
| `last_scan_id` | `TEXT` | nao | Scan em que o simbolo foi observado. |

Chave primaria: (`symbol`, `last_scan_id`).

### `scans`

Uma linha por execucao de `vitality scan`.

| Coluna | Tipo | Nulo | Descricao |
|---|---|---|---|
| `scan_id` | `TEXT` | nao | Identificador unico do scan. |
| `started_at` | `TEXT` | nao | Timestamp ISO 8601 de inicio. |
| `finished_at` | `TEXT` | sim | Timestamp ISO 8601 de fim; `NULL` indica scan incompleto. |

Chave primaria: `scan_id`.

## `vitality deps --format json`

Retorna a auditoria de dependencias declaradas contra chamadas observadas no
scan mais recente.

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

Exemplo gerado pelo reporter `dependency_audit.build_report`:

<!-- deps-json-example:start -->
```json
{
  "schema_version": "1.0",
  "scan_id": "scan-docs",
  "generated_at": "2026-06-24T12:02:00Z",
  "dependencies": [
    {
      "name": "pytest",
      "declared": true,
      "runtime_calls": 0,
      "status": "unused"
    },
    {
      "name": "requests",
      "declared": true,
      "runtime_calls": 12,
      "status": "used"
    }
  ]
}
```
<!-- deps-json-example:end -->

## `vitality query --module <path> --format json`

Retorna metricas estruturadas para um modulo presente nos dados do scan.

<!-- query-json-schema:start -->
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": [
    "schema_version",
    "module",
    "runtime_calls",
    "change_frequency_90d",
    "primary_authors",
    "has_test_coverage"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "1.0"
    },
    "module": {
      "type": "string"
    },
    "runtime_calls": {
      "type": "integer",
      "minimum": 0
    },
    "change_frequency_90d": {
      "type": "integer",
      "minimum": 0
    },
    "primary_authors": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "has_test_coverage": {
      "type": "boolean"
    }
  }
}
```
<!-- query-json-schema:end -->

Exemplo gerado pelo reporter `query.build_module_report`:

<!-- query-json-example:start -->
```json
{
  "schema_version": "1.0",
  "module": "src/payments/webhook.py",
  "runtime_calls": 12,
  "change_frequency_90d": 2,
  "primary_authors": [
    "ana",
    "maria"
  ],
  "has_test_coverage": true
}
```
<!-- query-json-example:end -->

## Versionamento

Os formatos JSON expostos pela CLI incluem o campo `schema_version`.
No MVP, o valor documentado e emitido e `"1.0"`.

Mudancas que removem ou renomeiam campos exigem incremento major. Mudancas
compatíveis, como adicionar campos opcionais, exigem incremento minor. O schema
SQLite e documentado junto dos contratos JSON para manter consumidores externos
e agentes alinhados com os dados persistidos.
