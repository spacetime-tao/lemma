from lemma.cli.problem_views import human_topic_label


def test_human_topic_label() -> None:
    assert "Logic" in human_topic_label("logic.propositional")
    assert human_topic_label("algebra.ring") != ""
