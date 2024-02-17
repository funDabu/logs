class Log_entry:
    """Data structure to store single access log entry"""

    __slots__ = (
        "ip_addr",
        "slot1",
        "slot2",
        "time",
        "request",
        "http_code",
        "bytes",
        "referer",
        "user_agent",
        "length",
    )

    def __init__(self):
        self.length = 0

    def __str__(self) -> str:
        content = [getattr(self, self.__slots__[i]) for i in range(self.length)]
        content = ", ".join(content)
        return f"[{content}]"

    def __repr__(self) -> str:
        return self.__str__()

    def __len__(self):
        return self.length
