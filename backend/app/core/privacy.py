import re

from app.models.enums import MatchType, PrivacyAction, PrivacyTarget
from app.models.privacy import PrivacyRule


def _match_value(value: str | None, rule: PrivacyRule) -> bool:
    if value is None:
        return False

    if rule.match_type == MatchType.equals:
        return value.lower() == rule.pattern.lower()
    if rule.match_type == MatchType.contains:
        return rule.pattern.lower() in value.lower()
    if rule.match_type == MatchType.regex:
        try:
            return re.search(rule.pattern, value) is not None
        except re.error:
            return False
    return False


def apply_privacy_rules(
    rules: list[PrivacyRule],
    app_name: str | None,
    window_title: str | None,
) -> tuple[str | None, str | None, bool]:
    ignore = False

    for rule in rules:
        if not rule.enabled:
            continue

        value = app_name if rule.target == PrivacyTarget.app_name else window_title
        if not _match_value(value, rule):
            continue

        if rule.action == PrivacyAction.ignore:
            ignore = True
        elif rule.action == PrivacyAction.redact:
            if rule.target == PrivacyTarget.app_name:
                app_name = None
            else:
                window_title = None

    return app_name, window_title, ignore
