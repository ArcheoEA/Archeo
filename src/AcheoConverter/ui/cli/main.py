# ui/cli/main.py

"""
Command-line interface for ArcheoConverter.
"""

import argparse
import sys
from pathlib import Path
import logging

from core.model_store import ArchiModel
from import_export.archimate_parser import parse_archimate_xml
from converter.version_migrator import VersionMigrator
from comparison.differ import ModelDiffer


def main():
    """Main CLI entrypoint."""
    
    parser = argparse.ArgumentParser(
        prog="ArcheoConverter",
        description="Architectural model converter and comparator"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert model between versions")
    convert_parser.add_argument("-i", "--input", required=True, type=Path, help="Input ArchiMate XML file")
    convert_parser.add_argument("-o", "--output", required=True, type=Path, help="Output ArchiMate XML file")
    convert_parser.add_argument("--from-version", default="3.2", choices=["3.2", "4.0"])
    convert_parser.add_argument("--to-version", default="4.0", choices=["3.2", "4.0"])
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two models")
    compare_parser.add_argument("-a", "--model-a", required=True, type=Path)
    compare_parser.add_argument("-b", "--model-b", required=True, type=Path)
    compare_parser.add_argument("--output", type=Path, help="Output JSON file for diff report")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search model elements")
    search_parser.add_argument("-i", "--input", required=True, type=Path)
    search_parser.add_argument("--name", help="Name pattern to search (supports regex)")
    search_parser.add_argument("--type", help="Element type filter")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)-8s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    logger = logging.getLogger("ArcheoConverter")
    
    try:
        if args.command == "convert":
            _handle_convert(args, logger)
        elif args.command == "compare":
            _handle_compare(args, logger)
        elif args.command == "search":
            _handle_search(args, logger)
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def _handle_convert(args, logger):
    """Handle convert command."""
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Load model
    result = parse_archimate_xml(input_path)
    
    model = ArchiModel(
        id=result.model_id,
        name=result.model_name,
        version=result.version,
        elements=[],
        relationships=[]
    )
    for elem in result.elements:
        model.add_element(elem)
    
    logger.info(f"Loaded model: {model.name} (v{model.version})")
    
    # Migrate
    migrator = VersionMigrator()
    migration_result = migrator.migrate(
        model,
        args.from_version,
        args.to_version
    )
    
    logger.info(f"Migrated to ArchiMate v{args.to_version}")
    if migration_result.warnings:
        for w in migration_result.warnings:
            logger.warning(f"Migration warning: {w}")


def _handle_compare(args, logger):
    """Handle compare command."""
    
    model_a = _load_model(args.model_a)
    model_b = _load_model(args.model_b)
    
    differ = ModelDiffer()
    result = differ.compare(model_a, model_b)
    
    logger.info(f"Comparison complete:")
    logger.info(f"- Model A: {result.model_a_name} ({len(result.model_a.elements)} elements)")
    logger.info(f"- Model B: {result.model_b_name} ({len(result.model_b.elements)} elements)")
    logger.info(f"- Match score: {result.match_score}")
    
    if result.element_diffs:
        added = sum(1 for d in result.element_diffs if d.type == "added")
        removed = sum(1 for d in result.element_diffs if d.type == "removed")
        modified = sum(1 for d in result.element_diffs if d.type == "modified")
        
        logger.info(f"- Differences: +{added} added, -{removed} removed, ~{modified} modified")


def _handle_search(args, logger):
    """Handle search command."""
    
    model = _load_model(Path(args.input))
    
    name_pattern = args.name
    type_filter = args.type
    
    if not any([name_pattern, type_filter]):
        logger.error("At least one filter (--name or --type) is required")
        return
    
    results = []
    for elem in model.elements.values():
        match = True
        
        if name_pattern and name_pattern.lower() not in elem.name.lower():
            match = False
        if type_filter and str(elem.type) != type_filter:
            match = False
            
        if match:
            results.append(elem)
    
    logger.info(f"Search found {len(results)} elements")
    for r in results[:10]:
        logger.info(f"- {r.name} ({r.type})")


def _load_model(path: Path) -> ArchiModel:
    """Helper to load a model from XML."""
    result = parse_archimate_xml(path)
    
    model = ArchiModel(
        id=result.model_id,
        name=result.model_name,
        version=result.version,
        elements=[],
        relationships=[]
    )
    for elem in result.elements:
        model.add_element(elem)
    return model


if __name__ == "__main__":
    main()
