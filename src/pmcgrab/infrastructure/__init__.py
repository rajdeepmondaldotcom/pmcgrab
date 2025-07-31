"""Infrastructure layer providing concrete implementations for external integrations.

This package contains the infrastructure layer of PMCGrab, implementing all
interactions with external systems, services, and resources. It provides
concrete implementations of the abstractions used by the application and
domain layers.

The infrastructure layer is responsible for all "dirty" concerns like network
communication, file system operations, configuration management, and external
API integrations. This separation enables the core business logic to remain
pure and testable.

Infrastructure Responsibilities:
    * **External API Integration**: HTTP clients for NCBI and PMC services
    * **Configuration Management**: Settings loading and environment variables
    * **File System Operations**: Directory management and file I/O
    * **Network Communication**: Robust HTTP handling with retries
    * **Resource Management**: Connection pooling and resource cleanup
    * **Error Translation**: Convert infrastructure errors to domain exceptions

Architectural Constraints:
    * **One-Way Dependency**: Can import from application and domain layers
    * **No Reverse Dependencies**: Application/domain layers cannot import infrastructure
    * **Concrete Implementations**: Only concrete classes, no abstractions
    * **External Concerns**: Handles all interaction with external systems
    * **Testability**: Provides test doubles and mocks for testing

Key Components:
    * **settings**: Configuration management and environment variable handling
    * **HTTP Clients**: Robust HTTP communication with external APIs
    * **File Handlers**: File system operations and directory management
    * **API Wrappers**: Concrete implementations of external service integrations
    * **Resource Managers**: Connection pools and resource lifecycle management

Configuration Management:
    The settings module provides centralized configuration management with
    support for environment variables, default values, and runtime configuration:

    ```python
    from pmcgrab.infrastructure.settings import next_email

    # Get email for NCBI API requests with round-robin rotation
    email = next_email()
    ```

Integration Patterns:
    * **Dependency Injection**: Infrastructure services injected into application layer
    * **Factory Pattern**: Create infrastructure objects based on configuration
    * **Adapter Pattern**: Adapt external APIs to internal interfaces
    * **Facade Pattern**: Simplify complex external system interactions

Error Handling:
    * **Network Error Recovery**: Automatic retries with exponential backoff
    * **Timeout Management**: Configurable timeouts for external requests
    * **Circuit Breaker**: Prevent cascading failures from external services
    * **Graceful Degradation**: Continue processing when non-critical services fail

Performance Optimization:
    * **Connection Pooling**: Reuse HTTP connections for better performance
    * **Request Caching**: Cache responses to reduce external API calls
    * **Batch Operations**: Optimize external API usage with batching
    * **Resource Cleanup**: Proper cleanup of system resources

Testing Support:
    * **Mock Infrastructure**: Test doubles for external dependencies
    * **Configuration Override**: Test-specific configuration settings
    * **Network Simulation**: Simulate network conditions and failures
    * **Resource Isolation**: Isolated test environments

External Service Integration:
    PMCGrab integrates with multiple external services through this layer:

    * **NCBI Entrez**: Article metadata and XML retrieval
    * **PMC OAI-PMH**: Large-scale metadata harvesting
    * **PMC OA Service**: Open access article information
    * **ID Converter**: Publication identifier conversion
    * **BioC API**: Structured biomedical text data

Example Usage:
    ```python
    # Infrastructure layer provides concrete implementations
    from pmcgrab.infrastructure.settings import next_email
    from pmcgrab.http_utils import cached_get

    # Configuration management
    email = next_email()

    # Robust HTTP communication
    response = cached_get("https://api.example.com/data",
                         params={"email": email})
    ```

Deployment Considerations:
    * **Environment Configuration**: Support for different deployment environments
    * **Resource Limits**: Respect system and API rate limits
    * **Monitoring Integration**: Logging and metrics for operational visibility
    * **Security**: Secure handling of credentials and sensitive data

Note:
    The infrastructure layer is where PMCGrab touches the real world. It's
    designed to be robust, configurable, and replaceable without affecting
    the core business logic. This enables PMCGrab to work in different
    environments and with different external service configurations.
"""
