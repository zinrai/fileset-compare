# fileset-compare

A command-line tool to compare file lists across multiple directories with name normalization.

## Overview

`fileset-compare` compares files across multiple directories based on their base names (filename without extension). It can apply string replacement rules to normalize file names before comparison.

## Features

- Compare 2 or more directories simultaneously
- Apply multiple find-and-replace rules to normalize file names
- Exclude specific paths from comparison
- Search subdirectories recursively
- Categorize results by directory presence

## Usage

### Basic Syntax

```bash
$ fileset-compare --dir <PATH> --dir <PATH> [OPTIONS]
```

### Options

- `--dir PATH`: Directory to compare (required, specify at least 2 times)
- `--match STRING`: Substring to find in filenames (pair with `--replace`)
- `--replace STRING`: String to replace matched substring (follows `--match`)
- `--exclude PATTERN`: Exclude paths containing pattern (can specify multiple times)
- `--recursive`: Search subdirectories recursively
- `--help`: Show help message
- `--version`: Show version information

### Examples

#### Basic Comparison

Compare two directories recursively:

```bash
$ fileset-compare --dir ./kubernetes --dir ./nomad --recursive
```

#### With Name Normalization

Normalize file names by replacing underscores with hyphens:

```bash
$ fileset-compare \
  --dir ./kubernetes \
  --dir ./nomad \
  --match "_" --replace "-" \
  --recursive
```

#### Multiple Normalization Rules

Apply multiple normalization rules in sequence:

```bash
$ fileset-compare \
  --dir ./kubernetes \
  --dir ./nomad \
  --dir ./terraform \
  --match "_" --replace "-" \
  --match ".template" --replace "" \
  --match "-prod" --replace "" \
  --recursive
```

This transforms file names like:

- `service_name.template.yaml` -> `service-name`
- `app-prod.k8s.yml` -> `app.k8s`

#### With Exclusions

Exclude common directories from comparison:

```bash
$ fileset-compare \
  --dir ./project-a \
  --dir ./project-b \
  --exclude node_modules \
  --exclude .git \
  --exclude .terraform \
  --recursive
```

## Output Format

The tool categorizes files by their directory presence:

```
Comparing 3 directories:
  - ./kubernetes
  - ./nomad
  - ./terraform

Normalization rules (2):
  '_' -> '-'
  '.template' -> ''

Recursive: True

============================================================
Collected 25 files from: kubernetes
Collected 22 files from: nomad
Collected 18 files from: terraform
============================================================

--- Files present only in: [kubernetes] ---
  auth-service
  monitoring-config

--- Files present only in: [nomad] ---
  legacy-app

--- Files present in: [kubernetes, nomad] ---
  api-gateway
  database-service

--- Files present in: [kubernetes, terraform] ---
  infrastructure-core

--- Files present in all directories: [kubernetes, nomad, terraform] ---
  shared-config

============================================================
Total unique files (normalized): 45
Categories: 5
```

## How It Works

1. **File Collection**: Scans each specified directory for files (optionally recursive)
2. **Base Name Extraction**: Extracts the base name (filename without extension) from each file
3. **Normalization**: Applies find-and-replace rules in the order specified
4. **Set Operations**: Uses Python sets for comparison across directories
5. **Categorization**: Groups files by which directories contain them
6. **Output**: Displays results grouped by directory presence

## Limitations

- **Exclusion patterns** use simple substring matching (not regex or glob)
- **File content** is not compared, only file names
- **Symbolic links** are followed by default

## License

This project is licensed under the [MIT License](./LICENSE).
