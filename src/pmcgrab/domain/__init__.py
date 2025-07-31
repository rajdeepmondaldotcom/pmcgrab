"""Pure domain models and value objects for PMCGrab core business logic.

This package contains the inner domain layer of PMCGrab, implementing core
business concepts and value objects without any external dependencies or
side effects. This design ensures maximum testability, reusability, and
independence from infrastructure concerns.

The domain layer represents the heart of PMCGrab's business logic, containing
the fundamental concepts and operations that define how PMC article data is
structured, processed, and manipulated throughout the system.

Domain Principles:
    * **Pure Functions**: No side effects, predictable behavior
    * **No External Dependencies**: Self-contained business logic
    * **Framework Independence**: Not tied to specific technologies
    * **Testability**: Easy to unit test in isolation
    * **Reusability**: Can be used across different contexts

Core Concepts:
    * **Value Objects**: Immutable objects representing domain concepts
    * **Data Structures**: Specialized collections for PMC processing
    * **Business Rules**: Core logic for data validation and transformation
    * **Domain Services**: Pure functions for complex domain operations

Key Components:
    * **BasicBiMap**: Bidirectional mapping for efficient cross-reference handling
    * **Domain Utilities**: Helper functions for data manipulation
    * **Value Validators**: Functions for ensuring data integrity
    * **Type Definitions**: Domain-specific type annotations

Architecture Benefits:
    * **Dependency Inversion**: Higher layers depend on this stable core
    * **Testability**: Pure functions enable comprehensive unit testing
    * **Maintainability**: Clear separation of business logic from infrastructure
    * **Extensibility**: Easy to add new domain concepts and rules

Usage Patterns:
    The domain layer is used throughout PMCGrab for:
    * Cross-reference management in XML processing
    * Data structure manipulation and transformation
    * Business rule validation and enforcement
    * Type-safe operations on domain data

Example Usage:
    ```python
    from pmcgrab.domain import BasicBiMap

    # Create bidirectional reference map
    ref_map = BasicBiMap()
    ref_map[0] = "<xref>Figure 1</xref>"

    # Efficient bidirectional lookup
    xml_element = ref_map[0]
    reference_id = ref_map.reverse["<xref>Figure 1</xref>"]
    ```

Integration:
    This package is imported by:
    * Application layer for business logic implementation
    * Common utilities for data processing
    * Infrastructure layer for domain model serialization
    * Test suites for isolated business logic testing

Note:
    The domain layer is intentionally minimal and focused. It contains only
    the essential concepts needed for PMC article processing, with all
    infrastructure concerns handled in other layers of the architecture.
"""

from pmcgrab.domain.value_objects import BasicBiMap

__all__: list[str] = [
    "BasicBiMap",
]
