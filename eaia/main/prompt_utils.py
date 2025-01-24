from langsmith import trace


class p(str):
    def __init__(self, tmpl: str, /, name: str = "Prompt"):
        self.tmpl = tmpl
        self.name = name

    def format(self, *args, **kwargs):
        with trace(name=self.name, run_type="prompt", inputs=kwargs) as rt:
            res = self.tmpl.format(*args, **kwargs)
            rt.add_outputs({"output": res})
            return res

    def __str__(self) -> str:
        return self.tmpl

    def __repr__(self) -> str:
        return repr(self.tmpl)

    def __len__(self) -> int:
        return len(self.tmpl)

    def __contains__(self, item) -> bool:
        return item in self.tmpl

    def __add__(self, other) -> "p":
        return p(self.tmpl + str(other))

    def __radd__(self, other) -> "p":
        return p(str(other) + self.tmpl)
