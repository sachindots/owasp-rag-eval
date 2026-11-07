from .schemas import Chunk


def spotlight(chunk: Chunk) -> str:
    """Render a chunk for the prompt so the model can tell retrieved data from instructions.

    Pick a technique and record it in PLAN.md: delimiters with a random boundary, datamarking
    (interleaving a marker between words), or encoding. Untrusted chunks matter most. The attack
    suite is this function's test: run it with and without `--defenses spotlight`.
    """
    raise NotImplementedError


def injection_score(text: str) -> float:
    """Probability in [0, 1] that `text` carries a prompt injection.

    A reasonable baseline is meta-llama/Llama-Prompt-Guard-2-86M from Hugging Face; your own
    classifier is a stretch goal. Pick the threshold on a held-out slice of the attack suite,
    never on the cases you report.
    """
    raise NotImplementedError
