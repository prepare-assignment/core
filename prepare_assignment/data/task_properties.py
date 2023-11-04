from dataclasses import dataclass


@dataclass
class TaskProperties:
    organization: str
    name: str
    version: str

    def __str__(self):
        v = "" if self.version == "latest" else f"@{self.version}"
        o = "" if self.organization == "prepare-assignment" else f"/{self.organization}"
        return f"{o}{self.name}{v}"
