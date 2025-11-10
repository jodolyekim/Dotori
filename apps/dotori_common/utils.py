from dataclasses import dataclass
@dataclass
class ApiResponse:
    ok: bool
    message: str|None = None
    data: dict|list|None = None
    def to_dict(self):
        out = {"ok": self.ok}
        if self.message: out["message"] = self.message
        if self.data is not None: out["data"] = self.data
        return out
