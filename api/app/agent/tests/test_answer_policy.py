from app.agent.answer_policy import AgentAnswerPolicy


def test_answer_policy_formats_inline_bullets_as_markdown_list() -> None:
    result = AgentAnswerPolicy().apply(
        "Je peux vous aider à : - Lister les feuilles - Examiner les colonnes",
    )

    assert result.answer == (
        "Je peux vous aider à:\n"
        "- Lister les feuilles\n"
        "- Examiner les colonnes"
    )
    assert result.blocked is False


def test_answer_policy_strips_boilerplate_introduction_heading() -> None:
    result = AgentAnswerPolicy().apply(
        "## Introduction\n\nBonjour, je peux vous aider avec Excel.",
    )

    assert result.answer == "Bonjour, je peux vous aider avec Excel."
    assert result.blocked is False
