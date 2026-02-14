"""
OrA Core - Constitutional governance and authority enforcement
"""

from .constitution import (
    Constitution,
    Operation,
    ConstitutionalConstraint,
    ConstitutionError,
    ConstitutionalViolation,
    PrimeDirectiveViolation,
    InsufficientAuthorityViolation,
    ProhibitedOperationViolation,
)

from .authority import (
    AuthorityLevel,
    AuthorityRequirements,
    get_authority_requirements,
    is_operation_authorized,
    get_byzantine_quorum_size,
)

from .kernel import OraKernel, Alert

__all__ = [
    "Constitution",
    "Operation",
    "ConstitutionalConstraint",
    "ConstitutionError",
    "ConstitutionalViolation",
    "PrimeDirectiveViolation",
    "InsufficientAuthorityViolation",
    "ProhibitedOperationViolation",
    "AuthorityLevel",
    "AuthorityRequirements",
    "get_authority_requirements",
    "is_operation_authorized",
    "get_byzantine_quorum_size",
    "OraKernel",
    "Alert",
]
