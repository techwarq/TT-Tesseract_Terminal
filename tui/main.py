from textual.containers import Vertical, Horizontal

def compose(self):
    yield Vertical(
        Static("Top"),
        Static("Middle"),
        Static("Bottom")
    )
