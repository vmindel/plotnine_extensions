import inspect
import re
from pathlib import Path

import pytest

import plotnine_extensions as pnx
from plotnine_extensions._skills.install import (
    bundled_skill_dir,
    install_skill,
    main,
)

SKILL = bundled_skill_dir()


def skill_files():
    return [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]


def parameters(obj):
    """Parameter names a function or plotnine geom/stat/position accepts."""
    if inspect.isclass(obj):
        # arguments every plotnine layer takes
        names = {"mapping", "data", "inherit_aes", "show_legend", "raster"}
        names |= set(inspect.signature(obj.__init__).parameters)
        names |= set(getattr(obj, "DEFAULT_PARAMS", {}))
        try:
            names |= set(obj.default_params)
        except (AttributeError, TypeError):
            pass
        names |= set(getattr(obj, "DEFAULT_AES", {}))
        # A geom forwards its stat's parameters, e.g. geom_hex(bins=...)
        stat_name = getattr(obj, "DEFAULT_PARAMS", {}).get("stat")
        if isinstance(stat_name, str) and stat_name != "identity":
            from plotnine._utils.registry import Registry

            names |= set(Registry[f"stat_{stat_name}"].DEFAULT_PARAMS)
        return names
    return set(inspect.signature(obj).parameters)


def test_frontmatter_and_routes():
    text = (SKILL / "SKILL.md").read_text()
    front = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert front, "SKILL.md needs YAML frontmatter"
    fields = dict(line.split(": ", 1) for line in front.group(1).splitlines())
    assert fields["name"] == "plotnine-extensions"
    assert 100 < len(fields["description"]) <= 1024
    routed = set(re.findall(r"`(references/[\w.-]+)`", text))
    on_disk = {f"references/{p.name}" for p in (SKILL / "references").glob("*.md")}
    assert routed == on_disk, f"routed {routed} but on disk {on_disk}"


def test_mentions_only_real_api():
    names = set()
    for path in skill_files():
        names |= set(re.findall(r"\bpnx\.([A-Za-z_]\w*)", path.read_text()))
    missing = sorted(n for n in names if not hasattr(pnx, n))
    assert not missing, f"skill mentions pnx.{missing}, which is not exported"


def test_every_export_is_covered():
    text = " ".join(p.read_text() for p in skill_files())
    internal = {"RasterGroup"}
    missing = sorted(n for n in pnx.__all__ if n not in internal and n not in text)
    assert not missing, f"exports not in the skill: {missing}"


def test_signature_blocks_use_real_parameters():
    for path in skill_files():
        text = path.read_text()
        for name, args in re.findall(r"pnx\.(\w+)\(([^()]*(?:\([^()]*\)[^()]*)*)\)", text):
            # only top-level keywords: drop nested calls such as geom_point(...)
            top = re.sub(r"\([^()]*\)", "()", args)
            shown = set(re.findall(r"(\w+)=", top))
            params = parameters(getattr(pnx, name))
            assert shown <= params, f"{path.name}: {name} has no {shown - params}"


def test_docs_page_lists_every_reference():
    page = (Path(__file__).parents[1] / "docs" / "claude-skill.md").read_text()
    listed = set(re.findall(r"`(references/[\w.-]+)`", page))
    on_disk = {f"references/{p.name}" for p in (SKILL / "references").glob("*.md")}
    assert listed == on_disk, f"docs/claude-skill.md lists {listed}, on disk {on_disk}"


def test_install(tmp_path, capsys):
    dest = install_skill(tmp_path / "skills" / "plotnine-extensions")
    assert (dest / "SKILL.md").read_text() == (SKILL / "SKILL.md").read_text()
    assert {p.name for p in (dest / "references").glob("*.md")} == {
        p.name for p in (SKILL / "references").glob("*.md")
    }
    with pytest.raises(FileExistsError):
        install_skill(dest)
    install_skill(dest, force=True)
    assert main(["--dest", str(dest)]) == 1
    assert main(["--dest", str(dest), "--force"]) == 0
    assert main(["--print-path"]) == 0
    assert capsys.readouterr().out.strip().endswith(str(SKILL))
