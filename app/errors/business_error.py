class BusinessError(Exception):
    """도메인(업무) 규칙 위반을 나타내는 공통 예외."""

    def __init__(self, message: str, code: str = "BUSINESS_ERROR") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
