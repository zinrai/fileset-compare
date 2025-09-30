#!/usr/bin/env python3
"""
fileset-compare: Compare file lists across multiple directories with name normalization.

This tool compares files across multiple directories based on their base names
(filename without extension), applying string replacement rules to
normalize file names before comparison.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class MatchReplaceAction(argparse.Action):
    """Custom action to handle --match and --replace pairs."""

    def __call__(self, parser, namespace, values, option_string=None):
        # Initialize replacements list if not exists
        if not hasattr(namespace, "replacements"):
            namespace.replacements = []

        if option_string == "--match":
            # Add new match entry
            namespace.replacements.append({"match": values, "replace": None})
            return

        if option_string != "--replace":
            return

        # Handle --replace option
        if not namespace.replacements:
            parser.error("--replace must be preceded by --match")

        if namespace.replacements[-1]["replace"] is not None:
            parser.error("--replace must follow its corresponding --match")

        # Complete the pair
        namespace.replacements[-1]["replace"] = values


def normalize_filename(filename: str, replacements: List[Dict[str, str]]) -> str:
    """
    Apply replacement rules in order to normalize a filename.

    Args:
        filename: The filename to normalize
        replacements: List of replacement rules (dict with 'match' and 'replace' keys)

    Returns:
        Normalized filename
    """
    normalized = filename
    for rule in replacements:
        match = rule["match"]
        replace = rule["replace"] if rule["replace"] is not None else ""
        normalized = normalized.replace(match, replace)
    return normalized


def should_exclude(path: Path, exclude_patterns: List[str]) -> bool:
    """
    Check if a path should be excluded based on patterns.

    Args:
        path: Path object to check
        exclude_patterns: List of exclusion patterns (substring match)

    Returns:
        True if path should be excluded, False otherwise
    """
    if not exclude_patterns:
        return False

    path_str = str(path)
    for pattern in exclude_patterns:
        if pattern in path_str:
            return True
    return False


def collect_files(
    directory: str,
    recursive: bool,
    replacements: List[Dict[str, str]],
    exclude_patterns: List[str],
) -> Set[str]:
    """
    Collect and normalize file names from a directory.

    Args:
        directory: Directory path to scan
        recursive: Whether to search recursively
        replacements: List of normalization rules
        exclude_patterns: List of exclusion patterns

    Returns:
        Set of normalized file names (base names without extensions)
    """
    path = Path(directory)

    if not path.exists():
        raise ValueError(f"Directory not found: {directory}")
    if not path.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    # Choose glob pattern based on recursive flag
    if recursive:
        files = path.rglob("*")
    else:
        files = path.glob("*")

    normalized_names = set()
    for file_path in files:
        # Skip if excluded
        if should_exclude(file_path, exclude_patterns):
            continue

        # Only process files (not directories)
        if not file_path.is_file():
            continue

        # Get base name (filename without extension)
        basename = file_path.stem
        # Apply normalization rules
        normalized = normalize_filename(basename, replacements)
        normalized_names.add(normalized)

    return normalized_names


def find_directories_containing_file(
    filename: str, dir_filesets: Dict[str, Set[str]]
) -> Tuple[str, ...]:
    """
    Find which directories contain the given filename.

    Args:
        filename: The filename to search for
        dir_filesets: Dictionary mapping directory paths to their file sets

    Returns:
        Tuple of directory paths that contain the filename
    """
    present_in_list = []
    for directory in dir_filesets.keys():
        if filename not in dir_filesets[directory]:
            continue
        present_in_list.append(directory)
    return tuple(present_in_list)


def compare_filesets(
    dir_filesets: Dict[str, Set[str]],
) -> Dict[Tuple[str, ...], List[str]]:
    """
    Compare file sets and categorize by directory presence.

    Args:
        dir_filesets: Dictionary mapping directory paths to their file sets

    Returns:
        Dictionary mapping directory tuples to lists of files present in those directories
    """
    # Get all unique file names across all directories
    all_files = set().union(*dir_filesets.values())

    # Categorize files by which directories they appear in
    results = {}
    for filename in all_files:
        present_in = find_directories_containing_file(filename, dir_filesets)

        if present_in not in results:
            results[present_in] = []
        results[present_in].append(filename)

    return results


def sort_key_for_results(item):
    """
    Sort key function for results.

    Sorts by:
    1. Number of directories (ascending)
    2. Directory names (alphabetically)

    Args:
        item: Tuple of (directories_tuple, files_list)

    Returns:
        Tuple used as sort key
    """
    dirs, files = item
    return (len(dirs), dirs)


def format_output(results: Dict[Tuple[str, ...], List[str]], dir_count: int):
    """
    Format and print comparison results.

    Args:
        results: Dictionary mapping directory tuples to file lists
        dir_count: Total number of directories being compared
    """
    # Sort results by number of directories (ascending), then by directory names
    sorted_results = sorted(results.items(), key=sort_key_for_results)

    for dirs, files in sorted_results:
        # Create directory names list
        dir_name_list = []
        for d in dirs:
            dir_name_list.append(Path(d).name)
        dir_names = ", ".join(dir_name_list)

        # Determine the header text
        if len(dirs) == 1:
            header = f"--- Files present only in: [{dir_names}] ---"
        elif len(dirs) == dir_count:
            header = f"--- Files present in all directories: [{dir_names}] ---"
        else:
            header = f"--- Files present in: [{dir_names}] ---"

        print(f"\n{header}")
        for filename in sorted(files):
            print(f"  {filename}")


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace):
    """
    Validate parsed arguments.

    Args:
        parser: ArgumentParser instance for error reporting
        args: Parsed arguments
    """
    # Validate minimum directory count
    if len(args.dir) < 2:
        parser.error("At least 2 directories must be specified")

    # Initialize replacements if not set
    if not hasattr(args, "replacements"):
        args.replacements = []

    # Validate that all match entries have corresponding replace
    for rule in args.replacements:
        if rule["replace"] is None:
            parser.error(f'--match "{rule["match"]}" is missing its --replace')

    # Initialize exclude_patterns if not set
    if not hasattr(args, "exclude") or args.exclude is None:
        args.exclude = []


def main():
    """Main entry point for fileset-compare."""
    parser = argparse.ArgumentParser(
        prog="fileset-compare",
        description="Compare file lists across multiple directories with name normalization.",
        epilog='Example: fileset-compare --dir /path/a --dir /path/b --match "_" --replace "-" --recursive',
    )

    parser.add_argument(
        "--dir",
        action="append",
        required=True,
        metavar="PATH",
        help="Directory to compare (specify at least 2 times)",
    )

    parser.add_argument(
        "--match",
        action=MatchReplaceAction,
        metavar="STRING",
        help="Substring to find in filenames (pair with --replace)",
    )

    parser.add_argument(
        "--replace",
        action=MatchReplaceAction,
        metavar="STRING",
        help="String to replace matched substring (follows --match)",
    )

    parser.add_argument(
        "--exclude",
        action="append",
        metavar="PATTERN",
        help="Exclude paths matching pattern (can specify multiple times)",
    )

    parser.add_argument(
        "--recursive", action="store_true", help="Search subdirectories recursively"
    )

    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    # Parse arguments
    args = parser.parse_args()

    # Validate arguments
    try:
        validate_args(parser, args)
    except Exception as e:
        parser.error(str(e))

    # Print configuration summary
    print(f"Comparing {len(args.dir)} directories:")
    for d in args.dir:
        print(f"  - {d}")

    if args.replacements:
        print(f"\nNormalization rules ({len(args.replacements)}):")
        for rule in args.replacements:
            print(f"  '{rule['match']}' -> '{rule['replace']}'")

    if args.exclude:
        pint(f"\nExclusion patterns ({len(args.exclude)}):")
        for pattern in args.exclude:
            print(f"  - {pattern}")

    print(f"\nRecursive: {args.recursive}")
    print("\n" + "=" * 60)

    # Collect files from each directory
    dir_filesets = {}
    try:
        for directory in args.dir:
            dir_filesets[directory] = collect_files(
                directory, args.recursive, args.replacements, args.exclude
            )
            print(
                f"Collected {len(dir_filesets[directory])} files from: {Path(directory).name}"
            )
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)

    # Compare file sets
    results = compare_filesets(dir_filesets)

    # Format and output results
    format_output(results, len(args.dir))

    # Summary
    total_files = len(set().union(*dir_filesets.values()))
    print(f"\n{'=' * 60}")
    print(f"Total unique files (normalized): {total_files}")
    print(f"Categories: {len(results)}")


if __name__ == "__main__":
    main()
