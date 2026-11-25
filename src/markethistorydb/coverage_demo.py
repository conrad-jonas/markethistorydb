"""Never imported and never tested: lowers the coverage below 100 % on purpose (CI-T02)"""


def uncovered() -> int:
    """
    Returns 1. No test calls it, so its lines stay uncovered.

    :return: 1
    """
    return 1
