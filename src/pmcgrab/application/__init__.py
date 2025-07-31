"""pmcgrab.application

Application layer – orchestrates domain models and infrastructure to satisfy
use-cases.  This layer *may* depend on domain and common helpers, but **must not
import infrastructure details directly** (e.g. HTTP clients). Those are
injected through function parameters or composed in higher layers.
"""
