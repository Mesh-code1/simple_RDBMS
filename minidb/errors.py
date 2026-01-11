class MiniDBError(Exception):
    pass


class ParseError(MiniDBError):
    pass


class TableNotFoundError(MiniDBError):
    pass


class SchemaError(MiniDBError):
    pass


class ConstraintViolation(MiniDBError):
    pass


class AuthError(MiniDBError):
    pass
