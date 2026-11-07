from ..schemas import JudgeVerdict


def judge(question: str, reference_answer: str, candidate: str) -> JudgeVerdict:
    """Grade the candidate answer against the reference with settings.judge_model.

    Write the correctness rubric in GUIDELINES.md first and put the same rubric in the judge
    prompt, so a human label and a judge label mean the same thing. Ask for JSON matching
    JudgeVerdict and validate it with JudgeVerdict.model_validate_json.
    """
    raise NotImplementedError
