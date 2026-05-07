from evosql_platform.executor.safety import SQLSafetyInterceptor


def test_blocks_delete_statement() -> None:
    interceptor = SQLSafetyInterceptor(allowed_tables={"students"})
    result = interceptor.validate("DELETE FROM students")
    assert not result.allowed


def test_blocks_multi_statement() -> None:
    interceptor = SQLSafetyInterceptor(allowed_tables={"students"})
    result = interceptor.validate("SELECT * FROM students; SELECT 1")
    assert not result.allowed


def test_blocks_unauthorized_table() -> None:
    interceptor = SQLSafetyInterceptor(allowed_tables={"students"})
    result = interceptor.validate("SELECT * FROM teachers")
    assert not result.allowed
