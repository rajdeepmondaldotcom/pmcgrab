"""Infrastructure layer – integrations with the *outside world*.

Only concrete implementations live here: HTTP clients, configuration loading,
filesystem helpers, etc.  Code in this package is allowed to import from
*application* and *domain* layers but **not the other way around**.
"""
