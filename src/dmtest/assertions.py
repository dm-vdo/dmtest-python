def assert_raises(callback):
    failed = False
    try:
        callback()
    except Exception:
        failed = True

    assert failed


def assert_equal(actual, expected, message=None):
    if actual != expected:
        error_message = f"{message}: " if message else ""
        error_message += f"expected {expected}, but got {actual}"
        raise AssertionError(error_message)


def assert_near(actual, expected, delta, message=None):
    value = abs(expected - actual)
    if value > delta:
        error_message = f"{message}: " if message else ""
        error_message += f"expected {expected}, but got {actual}, which is not within {delta}"
        raise AssertionError(error_message)
