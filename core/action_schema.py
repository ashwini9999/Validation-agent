# core/action_schema.py

def _classify_intent(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ["accessibility", "a11y", "aria", "tablist", "screen reader", "contrast", "keyboard", "focus"]):
        return "a11y"
    if any(k in t for k in ["ux", "user experience", "usability", "onboarding", "tooltip", "cta", "navigation"]):
        return "ux"
    if any(k in t for k in ["brand", "branding", "logo", "palette", "typography"]):
        return "branding"
    return "a11y"
