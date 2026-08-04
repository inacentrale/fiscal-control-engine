from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from app.ras_audit.legal_rules import RasLegalRule, RasLegalRuleStatus
from app.ras_audit.tax_event_rules import (
    RasTaxEventRule,
    RasTaxEventRuleStatus,
    applicable_tax_event_rules,
)


class RasFactSource(StrEnum):
    GL = "gl"
    USER = "user"
    ORGANIZATION = "organization"
    LEGAL_DOCUMENT = "legal_document"


class RasRuleResolutionStatus(StrEnum):
    RESOLVED_PROVISIONAL = "resolved_provisional"
    EXEMPTION_PROVISIONAL = "exemption_provisional"
    NOT_APPLICABLE_THRESHOLD = "not_applicable_threshold"
    CURRENCY_MISMATCH = "currency_mismatch"
    MISSING_FACTS = "missing_facts"
    AMBIGUOUS = "ambiguous"
    BLOCKED_SOURCE_GAP = "blocked_source_gap"
    NO_APPLICABLE_RULE = "no_applicable_rule"
    NOT_APPLICABLE_TAX_EVENT = "not_applicable_tax_event"
    TAX_EVENT_DATE_MISMATCH = "tax_event_date_mismatch"


_CONDITION_FIELDS = (
    "jurisdiction",
    "regime",
    "operation_type",
    "residence_status",
    "stable_establishment_status",
    "ifu_status",
    "beneficiary_type",
    "payer_type",
    "service_use_location",
    "treaty_override_status",
    "exemption_status",
)
# ``regime`` classifies a legal rule family; it is derived from the explicit
# transaction facts (residence, operation, exemption, etc.), not requested as
# an independent fact from the user. Jurisdiction is supplied by the request.
_IMPLICIT_REQUIRED_CONDITION_FIELDS = tuple(
    field for field in _CONDITION_FIELDS if field not in {"jurisdiction", "regime"}
)
_AMOUNT_FACTS = frozenset(
    {"tax_base_amount", "payment_amount", "gross_rent_excluding_vat"}
)
_DATE_FACTS = frozenset({"payment_date", "tax_period_end_date"})
_ALLOWED_FACTS = frozenset(_CONDITION_FIELDS) | _AMOUNT_FACTS | {
    "currency",
    "exemption_evidence",
    "scope_source_confirmation",
    "treaty_source_confirmation",
    "payment_status",
    "rent_accrual_status",
    *_DATE_FACTS,
}


@dataclass(frozen=True)
class RasLegalFact:
    name: str
    value: str
    source: RasFactSource
    evidence_reference: str

    def __post_init__(self) -> None:
        name = self.name.strip()
        value = self.value.strip()
        evidence_reference = self.evidence_reference.strip()
        if name not in _ALLOWED_FACTS:
            raise ValueError(f"unknown RAS legal fact: {name}")
        if not value or not evidence_reference:
            raise ValueError("RAS legal fact value and evidence are required")
        if name in _AMOUNT_FACTS:
            try:
                amount = Decimal(value)
            except InvalidOperation as exc:
                raise ValueError(f"invalid amount fact: {name}") from exc
            if not amount.is_finite() or amount < 0:
                raise ValueError(f"invalid amount fact: {name}")
        if name in _DATE_FACTS:
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(f"invalid date fact: {name}") from exc
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "evidence_reference", evidence_reference)


@dataclass(frozen=True)
class RasRuleResolutionRequest:
    transaction_date: date
    facts: tuple[RasLegalFact, ...]
    jurisdiction: str = "BF"

    def __post_init__(self) -> None:
        names = tuple(fact.name for fact in self.facts)
        if len(set(names)) != len(names):
            raise ValueError("duplicate RAS legal fact")
        jurisdiction = self.jurisdiction.strip().upper()
        if not jurisdiction:
            raise ValueError("RAS jurisdiction is required")
        object.__setattr__(self, "jurisdiction", jurisdiction)


@dataclass(frozen=True)
class RasRuleEvidence:
    source_kind: str
    source_url: str
    source_locator: str
    source_sha256: str


@dataclass(frozen=True)
class RasRuleResolution:
    status: RasRuleResolutionStatus
    rule_id: str | None
    rule_version: str | None
    calculation_method: str | None
    rate_percent: Decimal | None
    missing_facts: tuple[str, ...]
    alternative_rule_ids: tuple[str, ...]
    evidence: tuple[RasRuleEvidence, ...]
    source_assurance: str | None
    fact_sources: tuple[tuple[str, str], ...]


class RasRuleResolver:
    def __init__(
        self,
        rules: tuple[RasLegalRule, ...],
        tax_event_rules: tuple[RasTaxEventRule, ...] = (),
    ) -> None:
        if not rules:
            raise ValueError("RAS legal rules are required")
        self._rules = rules
        self._tax_event_rules = tax_event_rules

    def resolve(self, request: RasRuleResolutionRequest) -> RasRuleResolution:
        facts = {fact.name: fact.value for fact in request.facts}
        facts["jurisdiction"] = request.jurisdiction
        fact_sources = tuple(
            (fact.name, fact.source.value) for fact in request.facts
        ) + (("jurisdiction", RasFactSource.ORGANIZATION.value),)
        dated = tuple(
            rule
            for rule in self._rules
            if rule.valid_from <= request.transaction_date
            and (rule.valid_to is None or request.transaction_date <= rule.valid_to)
        )
        compatible = tuple(rule for rule in dated if _is_compatible(rule, facts))
        if not compatible:
            return _empty_resolution(
                RasRuleResolutionStatus.NO_APPLICABLE_RULE,
                fact_sources,
            )

        complete = tuple(
            rule for rule in compatible if not _missing_facts(rule, facts)
        )
        if complete:
            highest_priority = max(rule.priority for rule in complete)
            best = tuple(
                rule for rule in complete if rule.priority == highest_priority
            )
            if len(best) > 1:
                return RasRuleResolution(
                    status=RasRuleResolutionStatus.AMBIGUOUS,
                    rule_id=None,
                    rule_version=None,
                    calculation_method=None,
                    rate_percent=None,
                    missing_facts=(),
                    alternative_rule_ids=tuple(
                        sorted(rule.rule_id for rule in best)
                    ),
                    evidence=(),
                    source_assurance=None,
                    fact_sources=fact_sources,
                )
            event_gate = _tax_event_gate(
                rule=best[0],
                facts=facts,
                transaction_date=request.transaction_date,
                event_rules=self._tax_event_rules,
                fact_sources=fact_sources,
            )
            if event_gate is not None:
                return event_gate
            return _resolved(
                best[0],
                facts,
                fact_sources,
                _event_evidence(
                    best[0],
                    request.transaction_date,
                    self._tax_event_rules,
                ),
            )

        ranked = sorted(
            compatible,
            key=lambda rule: (
                len(_missing_facts(rule, facts)),
                -rule.priority,
                rule.rule_id,
            ),
        )
        minimum_missing = len(_missing_facts(ranked[0], facts))
        closest = tuple(
            rule
            for rule in ranked
            if len(_missing_facts(rule, facts)) == minimum_missing
            and rule.priority == ranked[0].priority
        )
        missing = tuple(
            sorted({fact for rule in closest for fact in _missing_facts(rule, facts)})
        )
        status = (
            RasRuleResolutionStatus.BLOCKED_SOURCE_GAP
            if all(
                rule.status is RasLegalRuleStatus.BLOCKED_MISSING_SCOPE_SOURCE
                for rule in closest
            )
            else RasRuleResolutionStatus.MISSING_FACTS
        )
        return RasRuleResolution(
            status=status,
            rule_id=None,
            rule_version=None,
            calculation_method=None,
            rate_percent=None,
            missing_facts=missing,
            alternative_rule_ids=tuple(sorted(rule.rule_id for rule in closest)),
            evidence=(),
            source_assurance=None,
            fact_sources=fact_sources,
        )


def _is_compatible(rule: RasLegalRule, facts: dict[str, str]) -> bool:
    return all(
        field not in facts
        or expected == "*"
        or facts[field] == expected
        for field in _CONDITION_FIELDS
        if (expected := str(getattr(rule, field)))
    )


def _missing_facts(rule: RasLegalRule, facts: dict[str, str]) -> tuple[str, ...]:
    required = set(rule.required_facts)
    required.update(
        field
        for field in _IMPLICIT_REQUIRED_CONDITION_FIELDS
        if str(getattr(rule, field)) != "*"
    )
    return tuple(sorted(required - facts.keys()))


def _resolved(
    rule: RasLegalRule,
    facts: dict[str, str],
    fact_sources: tuple[tuple[str, str], ...],
    event_evidence: RasRuleEvidence | None = None,
) -> RasRuleResolution:
    if rule.status is RasLegalRuleStatus.BLOCKED_MISSING_SCOPE_SOURCE:
        return RasRuleResolution(
            status=RasRuleResolutionStatus.BLOCKED_SOURCE_GAP,
            rule_id=None,
            rule_version=None,
            calculation_method=None,
            rate_percent=None,
            missing_facts=rule.required_facts,
            alternative_rule_ids=(rule.rule_id,),
            evidence=(),
            source_assurance=rule.source_assurance,
            fact_sources=fact_sources,
        )
    if (
        rule.amount_currency is not None
        and facts.get("currency", "").upper() != rule.amount_currency
    ):
        return _rule_resolution(
            RasRuleResolutionStatus.CURRENCY_MISMATCH,
            rule,
            fact_sources,
            event_evidence,
        )
    if rule.minimum_amount is not None:
        amount = _applicable_amount(rule, facts)
        if amount is not None and amount < rule.minimum_amount:
            return _rule_resolution(
                RasRuleResolutionStatus.NOT_APPLICABLE_THRESHOLD,
                rule,
                fact_sources,
                event_evidence,
            )
    status = (
        RasRuleResolutionStatus.EXEMPTION_PROVISIONAL
        if rule.rate_percent == 0
        else RasRuleResolutionStatus.RESOLVED_PROVISIONAL
    )
    return _rule_resolution(status, rule, fact_sources, event_evidence)


def _tax_event_gate(
    *,
    rule: RasLegalRule,
    facts: dict[str, str],
    transaction_date: date,
    event_rules: tuple[RasTaxEventRule, ...],
    fact_sources: tuple[tuple[str, str], ...],
) -> RasRuleResolution | None:
    if not event_rules or rule.rate_percent == 0:
        return None
    applicable = applicable_tax_event_rules(
        event_rules,
        jurisdiction=rule.jurisdiction,
        regime=rule.regime,
        event_date=transaction_date,
    )
    if len(applicable) != 1:
        return RasRuleResolution(
            status=RasRuleResolutionStatus.BLOCKED_SOURCE_GAP,
            rule_id=None,
            rule_version=None,
            calculation_method=None,
            rate_percent=None,
            missing_facts=("tax_event_rule",),
            alternative_rule_ids=(rule.rule_id,),
            evidence=(),
            source_assurance=None,
            fact_sources=fact_sources,
        )
    event_rule = applicable[0]
    evidence = _tax_event_evidence(event_rule)
    if event_rule.status is RasTaxEventRuleStatus.BLOCKED_MISSING_SOURCE:
        return _event_gate_resolution(
            RasRuleResolutionStatus.BLOCKED_SOURCE_GAP,
            rule,
            fact_sources,
            evidence,
            ("tax_event_source",),
        )
    if event_rule.event_fact not in facts:
        missing = (event_rule.event_fact,) + (
            (event_rule.event_date_fact,)
            if event_rule.event_date_fact not in facts
            else ()
        )
        return _event_gate_resolution(
            RasRuleResolutionStatus.MISSING_FACTS,
            rule,
            fact_sources,
            evidence,
            missing,
        )
    if facts[event_rule.event_fact] != event_rule.event_value:
        return _event_gate_resolution(
            RasRuleResolutionStatus.NOT_APPLICABLE_TAX_EVENT,
            rule,
            fact_sources,
            evidence,
            (),
        )
    if event_rule.event_date_fact not in facts:
        return _event_gate_resolution(
            RasRuleResolutionStatus.MISSING_FACTS,
            rule,
            fact_sources,
            evidence,
            (event_rule.event_date_fact,),
        )
    if date.fromisoformat(facts[event_rule.event_date_fact]) != transaction_date:
        return _event_gate_resolution(
            RasRuleResolutionStatus.TAX_EVENT_DATE_MISMATCH,
            rule,
            fact_sources,
            evidence,
            ("matching_tax_event_date",),
        )
    return None


def _event_gate_resolution(
    status: RasRuleResolutionStatus,
    rule: RasLegalRule,
    fact_sources: tuple[tuple[str, str], ...],
    evidence: RasRuleEvidence,
    missing_facts: tuple[str, ...],
) -> RasRuleResolution:
    return RasRuleResolution(
        status=status,
        rule_id=None,
        rule_version=None,
        calculation_method=None,
        rate_percent=None,
        missing_facts=missing_facts,
        alternative_rule_ids=(rule.rule_id,),
        evidence=(evidence,),
        source_assurance=None,
        fact_sources=fact_sources,
    )


def _event_evidence(
    rule: RasLegalRule,
    transaction_date: date,
    event_rules: tuple[RasTaxEventRule, ...],
) -> RasRuleEvidence | None:
    applicable = applicable_tax_event_rules(
        event_rules,
        jurisdiction=rule.jurisdiction,
        regime=rule.regime,
        event_date=transaction_date,
    )
    return _tax_event_evidence(applicable[0]) if len(applicable) == 1 else None


def _tax_event_evidence(rule: RasTaxEventRule) -> RasRuleEvidence:
    return RasRuleEvidence(
        source_kind="tax_event",
        source_url=rule.source_url,
        source_locator=rule.source_locator,
        source_sha256=rule.source_sha256,
    )


def _applicable_amount(
    rule: RasLegalRule,
    facts: dict[str, str],
) -> Decimal | None:
    for name in rule.required_facts:
        if name in _AMOUNT_FACTS and name in facts:
            return Decimal(facts[name])
    return None


def _rule_resolution(
    status: RasRuleResolutionStatus,
    rule: RasLegalRule,
    fact_sources: tuple[tuple[str, str], ...],
    event_evidence: RasRuleEvidence | None = None,
) -> RasRuleResolution:
    return RasRuleResolution(
        status=status,
        rule_id=rule.rule_id,
        rule_version=rule.version,
        calculation_method=rule.calculation_method.value,
        rate_percent=rule.rate_percent,
        missing_facts=(),
        alternative_rule_ids=(),
        evidence=(
            RasRuleEvidence(
                source_kind="scope",
                source_url=rule.scope_source_url,
                source_locator=rule.scope_source_locator,
                source_sha256=rule.scope_source_sha256,
            ),
            RasRuleEvidence(
                source_kind="rate",
                source_url=rule.rate_source_url,
                source_locator=rule.rate_source_locator,
                source_sha256=rule.rate_source_sha256,
            ),
        )
        + ((event_evidence,) if event_evidence is not None else ()),
        source_assurance=rule.source_assurance,
        fact_sources=fact_sources,
    )


def _empty_resolution(
    status: RasRuleResolutionStatus,
    fact_sources: tuple[tuple[str, str], ...],
) -> RasRuleResolution:
    return RasRuleResolution(
        status=status,
        rule_id=None,
        rule_version=None,
        calculation_method=None,
        rate_percent=None,
        missing_facts=(),
        alternative_rule_ids=(),
        evidence=(),
        source_assurance=None,
        fact_sources=fact_sources,
    )
