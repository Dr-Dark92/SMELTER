"""Controller-owned operation deadlines and result semantics shared by transports."""

DEFAULT_OPERATION_TIMEOUT = 120
FRONTEND_VALIDATION_TIMEOUT = 420
BRIDGE_RELAY_HEADROOM = 15
BRIDGE_RPC_TIMEOUT = 450


def operation_timeout(name):
    # Two fixed 180-second test processes plus image/snapshot/cleanup overhead.
    # Callers cannot widen this through model arguments or skill instructions.
    if name == 'rea_ghidra_analyze':
        return 210  # Fixed 180-second native import plus staging/cleanup overhead.
    return FRONTEND_VALIDATION_TIMEOUT if name == 'validate_frontend_workspace' else DEFAULT_OPERATION_TIMEOUT


def result_failed(result):
    """An expected TDD assertion failure is evidence; a runner error is a failure."""
    if not isinstance(result, dict):
        return True
    status = result.get('status')
    return status in {'error', 'rea_failed', 'mcp_failed', 'workspace_validation_failed'} or (
        status == 'coding_tests_failed' and result.get('stage') != 'RED')
