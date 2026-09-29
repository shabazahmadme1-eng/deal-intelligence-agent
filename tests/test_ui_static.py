"""Static UI contract: catches wiring/visual regressions without a browser.

- Every element ID referenced by the inline script must exist in the markup.
- Control labels must match the demo-script wording.
- Component buttons that restyle the generic `button` rule (light text on
  dark) must declare their own text color, or their text renders unreadable.
"""
import re
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / "static" / "index.html"


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_script_referenced_ids_exist():
    html = _page()
    ids = set(re.findall(r'id="([^"]+)"', html))
    script = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    refs = set(re.findall(r'\$\("([^"]+)"\)', script))
    assert refs, "expected inline script to reference element IDs"
    assert refs <= ids, f"missing IDs: {sorted(refs - ids)}"


def test_control_labels_match_demo_script():
    html = _page()
    for label in [
        "Brief me before the call",
        "Compare without memory",
        "Draft follow-up",
        "Suggest tactics",
        "Retain in memory",
        "Load demo data",
        "Reset",
    ]:
        assert label in html, f"label changed (demo_script.md references it): {label}"


def test_component_buttons_declare_text_color():
    css = re.search(r"<style>(.*)</style>", _page(), re.S).group(1)
    for selector in (".deal-btn",):
        block = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
        assert block, f"missing CSS rule: {selector}"
        # `color:` but not `border-color:` / `background-color:`.
        assert re.search(r"(?<![-\w])color\s*:", block.group(1)), (
            f"{selector} must declare its own text color: the generic button "
            "rule sets light-on-dark text, which is unreadable on a light card."
        )


def test_component_buttons_defend_their_background_on_hover():
    # `button:hover` flips the background to black. Any component restyling a
    # button must pin its own hover background, or hovering blanks the card.
    css = re.search(r"<style>(.*)</style>", _page(), re.S).group(1)
    for selector in (".deal-btn:hover", ".deal-btn.active:hover"):
        block = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
        assert block, f"missing CSS rule: {selector}"
        assert re.search(r"(?<![-\w])background\s*:", block.group(1)), (
            f"{selector} must declare a background: the generic button:hover "
            "rule would otherwise paint the card black with dark text on top."
        )
