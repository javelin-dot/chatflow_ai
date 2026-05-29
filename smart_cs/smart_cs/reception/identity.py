"""IdentityResolver — cross-channel user identity unification.

Stub for now. Real implementations bind external IDs (wechat_openid, email,
phone, employee_id) to a stable customer_id.
"""
from __future__ import annotations

from typing import Optional

from ..customer.customer import Customer


class IdentityResolver:
    def resolve(
        self,
        tenant_id: str,
        channel: str,
        external_id: Optional[str],
    ) -> Optional[Customer]:
        if not external_id:
            return None
        # Minimal stub: synthesize a customer keyed by channel+external_id.
        return Customer(
            id=f"{channel}:{external_id}",
            tenant_id=tenant_id,
        )
