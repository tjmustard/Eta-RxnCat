"""R26: ``eta_rxncat.thermo`` exports load lazily and its API is unchanged (slice 04)."""

import subprocess
import sys

import pytest

import eta_rxncat.thermo as thermo


@pytest.mark.parametrize("name", sorted(thermo.__all__))
def test_every_public_name_still_imports(name: str) -> None:
    """``from eta_rxncat.thermo import X`` works for every name in ``__all__``."""
    namespace: dict[str, object] = {}
    exec(f"from eta_rxncat.thermo import {name} as value", namespace)  # noqa: S102
    assert namespace["value"] is getattr(thermo, name)


def test_boltzmann_is_still_the_function() -> None:
    """The name shared with its submodule stays the function, whatever was imported first."""
    code = (
        "import eta_rxncat.thermo.boltzmann; import eta_rxncat.thermo as t; "
        "assert callable(t.boltzmann) and t.boltzmann.__name__ == 'boltzmann'"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_unknown_attribute_raises() -> None:
    """A name that is not exported is an AttributeError, not an import."""
    with pytest.raises(AttributeError, match="no_such_name"):
        thermo.no_such_name  # noqa: B018


def test_constants_import_leaves_rdkit_out() -> None:
    """``import eta_rxncat.thermo.constants`` does not load RDKit (the point of R26)."""
    code = (
        "import sys; import eta_rxncat.thermo.constants; "
        "assert 'rdkit' not in sys.modules, 'rdkit loaded'"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_lazy_names_load_rdkit_on_use() -> None:
    """A name that needs RDKit still works (and only then loads it)."""
    code = (
        "import sys, eta_rxncat.thermo as t; assert 'rdkit' not in sys.modules; "
        "t.rotational_symmetry_number; assert 'rdkit' in sys.modules"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
