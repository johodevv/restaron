"""Kitchen cancellation roles; every sent-item correction is audited by the caller."""
from fastapi import HTTPException


def kitchen_sent_quantity(item):
    quantity = max(0, int(item.quantity or 0))
    sent = max(0, int(item.sent_quantity or 0), int(item.prepared_quantity or 0))
    if sent:
        return min(quantity, sent)
    # Older records may have a flag/timestamp without the later quantity counter.
    if item.sent_to_kitchen or item.sent_to_kitchen_at:
        return quantity
    return 0


def require_kitchen_admin(user):
    role = user.role.value if hasattr(user.role, 'value') else str(user.role)
    if role not in ('admin', 'developer'):
        raise HTTPException(403, "Oshxonaga yuborilgan taomni faqat admin o‘chirishi yoki dona sonini kamaytirishi mumkin. Adminga murojaat qiling.")


def require_kitchen_item_editor(user):
    role = user.role.value if hasattr(user.role, 'value') else str(user.role)
    if role not in ('admin', 'developer', 'waiter'):
        raise HTTPException(403, "Oshxonaga yuborilgan taomni ofitsiant yoki admin o‘zgartirishi mumkin.")
