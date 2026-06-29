# Release

Procedimento para publicar `codebase-vitality` no PyPI.

## Prerequisites

- Python 3.10+
- Git worktree limpo
- PyPI credentials configuradas, preferencialmente via token:
  `TWINE_USERNAME=__token__` e `TWINE_PASSWORD=<pypi-token>`
- Ferramentas de release instaladas:

```bash
python3 -m pip install --upgrade build twine
```

## Build

```bash
python3 -m unittest discover -s tests
rm -rf dist build *.egg-info
python3 -m build
```

## Check

```bash
python3 -m twine check dist/*
```

## Upload

O upload exige PyPI credentials validas. Nao publique se os testes ou
`twine check` falharem.

```bash
python3 -m twine upload dist/*
```

## Install Verification

Depois do upload, valide em um ambiente limpo:

```bash
python3 -m pip install codebase-vitality
vitality --help
```

Para validar a versao exata deste release:

```bash
python3 -m pip install codebase-vitality==0.1.0
```
