# ai-generated: 90% - test cases written by an AI assistant, reviewed line by line by me
# Semgrep test file paired with rules.yml (P-31): each rule gets one true positive and one
# true negative, annotated with Semgrep's rule-id and ok comments.

def risky():
    raise ValueError("boom")


def broad_catch_bad():
    # ruleid: broad-except
    try:
        risky()
    except Exception:
        return None


def broad_catch_ok():
    # ok: broad-except
    try:
        risky()
    except ValueError:
        return None


def error_text_bad():
    try:
        risky()
    except ValueError as e:
        # ruleid: error-text-in-response
        return err(500, "internal", str(e))


def error_text_ok():
    try:
        risky()
    except ValueError:
        # ok: error-text-in-response
        return err(500, "internal", "internal error")


def err(status, code, message):
    return {"status": status, "code": code, "message": message}
