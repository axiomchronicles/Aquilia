"""Legacy project migration command."""

from dataclasses import dataclass


@dataclass
class MigrationResult:
    """Result of migration operation."""
    
    changes: list[str]


def migrate_legacy(
    dry_run: bool = False,
    verbose: bool = False,
) -> MigrationResult:
    """
    Migrate from Django-style layout to Aquilate.
    
    Args:
        dry_run: Preview migration without making changes
        verbose: Enable verbose output
    
    Returns:
        MigrationResult with list of changes
    """
    # TODO: Implement legacy migration
    raise NotImplementedError("Legacy migration not yet implemented")
