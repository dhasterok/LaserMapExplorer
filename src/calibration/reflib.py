"""Reference-material composition YAML schema, loader, validator, and writer.

Mirrors ``src/stoichiometry/config.py``'s dataclass+loader+validator idiom:
config lives as external YAML (``resources/calibration/reference_materials/*.yaml``),
with actionable errors on malformed input rather than silently computing a
wrong calibration factor.
"""
from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_ANALYTE_RE = re.compile(r"^([A-Za-z]{1,2})(\d+)$")

# Naming convention for a pooled-isotope virtual channel (see pooling.py) --
# owned here (not pooling.py) so resolve_elemental_value can recognize one
# without pooling.py needing to import reflib (avoiding an import cycle,
# since massbias.py -- which pooling.py already depends on -- imports reflib).
POOLED_TOTAL_SUFFIX = " total"

VALID_UNCERTAINTY_TYPES = {"1SD", "2SD", "95CI", "SEM", "2SE"}

# Divisor to normalize a stated uncertainty down to 1SD, so standards.py's
# z/t-test always operates in one consistent unit regardless of how the
# source publication reported it. SEM is left as-is (n-dependent conversion
# to SD isn't modeled here; SEM values are used directly as an SD-equivalent).
# 2SE is distinct from 2SD (standard error, not standard deviation, of the
# reported mean) but the two happen to share the same /2 divisor in this
# already-1SD-equivalent convention -- confirmed needed by NIST610's
# 143Nd/144Nd GeoREM entry, reported as 2SE, not 2SD.
_UNCERTAINTY_TO_1SD_DIVISOR = {
    "1SD": 1.0,
    "2SD": 2.0,
    "95CI": 1.959963984540054,
    "SEM": 1.0,
    "2SE": 2.0,
}


class ReferenceLibraryError(ValueError):
    """Raised for missing/malformed reference-material YAML fields."""


@dataclass
class ReferenceAnalyte:
    """A certified elemental (total-element) concentration for one analyte.

    Attributes
    ----------
    element : str
        Element symbol, e.g. ``"Pb"``.
    mass : int
        Nominal isotope mass the source row is keyed by.
    value : float or None
        Certified concentration in ``units``, or ``None`` for a placeholder
        entry.
    uncertainty : float or None
        Reported uncertainty on ``value`` in ``units``, or ``None``.
    uncertainty_type : str
        One of :data:`VALID_UNCERTAINTY_TYPES` (required when ``value`` is
        set); defaults to ``"1SD"`` for placeholder entries.
    units : str
        Concentration units, ``"ppm"`` by default.
    source : str
        Provenance string for the value.
    """

    element: str
    mass: int
    value: float | None
    uncertainty: float | None
    uncertainty_type: str
    units: str
    source: str

    def uncertainty_1sd(self) -> float | None:
        """Uncertainty normalized to one standard deviation.

        Returns
        -------
        float or None
            ``uncertainty`` divided by the
            :data:`_UNCERTAINTY_TO_1SD_DIVISOR` factor for
            ``uncertainty_type``, or ``None`` when ``uncertainty`` is
            ``None``.
        """
        if self.uncertainty is None:
            return None
        divisor = _UNCERTAINTY_TO_1SD_DIVISOR.get(self.uncertainty_type, 1.0)
        return self.uncertainty / divisor


@dataclass
class ReferenceIsotopeRatio:
    """A certified isotope-ratio reference value (e.g. GeoREM's ``206Pb/204Pb``).

    Distinct from :class:`ReferenceAnalyte`, which holds elemental
    concentration values. Used for mass-bias/radiogenic-ratio calibration,
    where natural-abundance scaling is not valid (see ``massbias.py``).

    Attributes
    ----------
    numerator_element, denominator_element : str
        Element symbols of the ratio numerator and denominator.
    numerator_mass, denominator_mass : int
        Isotope masses of the ratio numerator and denominator.
    value : float or None
        The certified ratio, or ``None`` for a placeholder entry.
    uncertainty : float or None
        Reported uncertainty on ``value``, or ``None``.
    uncertainty_type : str or None
        One of :data:`VALID_UNCERTAINTY_TYPES`, or ``None`` -- legitimately
        unknown even when ``value`` is populated (some GeoREM
        NIST612/614 rows report a value and uncertainty with no stated
        type; a warning is raised at parse time, see
        :func:`_parse_isotope_ratio`).
    source : str
        Provenance string for the value.
    """

    numerator_element: str
    numerator_mass: int
    denominator_element: str
    denominator_mass: int
    value: float | None
    uncertainty: float | None
    uncertainty_type: str | None
    source: str

    @property
    def numerator(self) -> str:
        """str: Numerator channel name, e.g. ``"Pb206"``."""
        return f"{self.numerator_element}{self.numerator_mass}"

    @property
    def denominator(self) -> str:
        """str: Denominator channel name, e.g. ``"Pb204"``."""
        return f"{self.denominator_element}{self.denominator_mass}"

    def uncertainty_1sd(self) -> float | None:
        """Uncertainty normalized to one standard deviation.

        Returns
        -------
        float or None
            ``uncertainty`` divided by the
            :data:`_UNCERTAINTY_TO_1SD_DIVISOR` factor for
            ``uncertainty_type``, or ``None`` when either ``uncertainty`` or
            ``uncertainty_type`` is ``None``.
        """
        if self.uncertainty is None or self.uncertainty_type is None:
            return None
        divisor = _UNCERTAINTY_TO_1SD_DIVISOR.get(self.uncertainty_type, 1.0)
        return self.uncertainty / divisor


@dataclass
class ReferenceMaterial:
    """A complete reference-material composition: analytes and isotope ratios.

    Attributes
    ----------
    standard : str
        Reference-material name (the library key), e.g. ``"NIST610"``.
    description : str
        Free-text description.
    source : str
        Provenance string for the material as a whole.
    analytes : dict[str, ReferenceAnalyte]
        Certified elemental concentrations, keyed by analyte column name.
    isotope_ratios : dict[str, ReferenceIsotopeRatio]
        Certified isotope ratios, keyed ``"<numerator>/<denominator>"``.
        Empty for concentration-only materials.
    """

    standard: str
    description: str
    source: str
    analytes: dict[str, ReferenceAnalyte]
    isotope_ratios: dict[str, ReferenceIsotopeRatio] = field(default_factory=dict)

    def value(self, analyte: str) -> float | None:
        """Certified concentration for ``analyte``.

        Parameters
        ----------
        analyte : str
            Analyte column name (exact key).

        Returns
        -------
        float or None
            The entry's ``value``, or ``None`` if there is no such entry.
        """
        entry = self.analytes.get(analyte)
        return entry.value if entry else None

    def uncertainty_1sd(self, analyte: str) -> float | None:
        """One-sigma uncertainty for ``analyte``'s certified concentration.

        Parameters
        ----------
        analyte : str
            Analyte column name (exact key).

        Returns
        -------
        float or None
            The entry's :meth:`ReferenceAnalyte.uncertainty_1sd`, or
            ``None`` if there is no such entry.
        """
        entry = self.analytes.get(analyte)
        return entry.uncertainty_1sd() if entry else None

    def ratio(self, numerator: str, denominator: str) -> ReferenceIsotopeRatio | None:
        """Certified isotope ratio for ``numerator / denominator``.

        Parameters
        ----------
        numerator : str
            Numerator channel name, e.g. ``"Pb206"``.
        denominator : str
            Denominator channel name, e.g. ``"Pb204"``.

        Returns
        -------
        ReferenceIsotopeRatio or None
            The exact-key entry if present; otherwise the flipped-key entry
            inverted (``value = 1 / value``, relative uncertainty
            preserved), since GeoREM sometimes reports only one direction
            (e.g. BCR-2 has ``208Pb/206Pb`` but not the reverse). ``None``
            if neither direction is available.
        """
        entry = self.isotope_ratios.get(f"{numerator}/{denominator}")
        if entry is not None:
            return entry
        flipped = self.isotope_ratios.get(f"{denominator}/{numerator}")
        if flipped is None or flipped.value is None:
            return None
        inv_unc = None
        if flipped.uncertainty is not None:
            # relative uncertainty is preserved under inversion: d(1/x)/x = -dx/x
            inv_unc = flipped.uncertainty / flipped.value ** 2
        return ReferenceIsotopeRatio(
            numerator_element=flipped.denominator_element, numerator_mass=flipped.denominator_mass,
            denominator_element=flipped.numerator_element, denominator_mass=flipped.numerator_mass,
            value=1.0 / flipped.value, uncertainty=inv_unc, uncertainty_type=flipped.uncertainty_type,
            source=flipped.source,
        )


def parse_analyte_name(analyte: str) -> tuple[str, int] | None:
    """Split an analyte column name into its element and mass.

    Parameters
    ----------
    analyte : str
        Column name, e.g. ``"Pb206"``.

    Returns
    -------
    tuple[str, int] or None
        ``(element, mass)``, or ``None`` if ``analyte`` does not match the
        ``<element><mass>`` convention used throughout this package.

    Notes
    -----
    Public so callers outside ``reflib``/``rawfile`` (e.g. the GUI's
    isotope-grouping table) do not need their own copy of ``_ANALYTE_RE``.
    """
    m = _ANALYTE_RE.match(analyte)
    if not m:
        return None
    return m.group(1), int(m.group(2))


def resolve_elemental_value(reference: ReferenceMaterial, analyte: str) -> ReferenceAnalyte | None:
    """Find the reference entry usable for an analyte's elemental calibration.

    Parameters
    ----------
    reference : ReferenceMaterial
        The reference material to look in.
    analyte : str
        An analyte column name (e.g. ``"U238"``) or a pooled-isotope
        virtual channel name (e.g. ``"Pb total"``, see ``pooling.py``).

    Returns
    -------
    ReferenceAnalyte or None
        The direct-key entry if present; otherwise the lowest-mass entry
        for the same element; ``None`` if the element is absent or
        ``analyte`` is unparseable.

    Notes
    -----
    GeoREM reports one row per element, not per isotope (an entry keyed
    ``"U238"`` holds elemental U, not a U238-specific value), so a sibling
    isotope with no key of its own (e.g. ``"U235"``) can validly reuse it.
    Calibration is a ratio (``CPS_sample / CPS_standard * ref_ppm``), so the
    natural-abundance fraction of whichever isotope is used cancels between
    sample and standard and is deliberately not applied -- the elemental
    value is returned unscaled for both the direct-key and fallback cases.
    A pooled channel resolves the same way, since the pooling fraction
    cancels just as a single isotope's abundance does.
    """
    entry = reference.analytes.get(analyte)
    if entry is not None:
        return entry
    if analyte.endswith(POOLED_TOTAL_SUFFIX):
        element = analyte[: -len(POOLED_TOTAL_SUFFIX)]
        candidates = sorted((a for a in reference.analytes.values() if a.element == element), key=lambda a: a.mass)
        return candidates[0] if candidates else None
    parsed = parse_analyte_name(analyte)
    if parsed is None:
        return None
    element, _ = parsed
    candidates = sorted((a for a in reference.analytes.values() if a.element == element), key=lambda a: a.mass)
    return candidates[0] if candidates else None


def _require(d: dict, key: str, context: str):
    """Return ``d[key]`` or raise a contextual error.

    Parameters
    ----------
    d : dict
        Mapping to read from.
    key : str
        Required key.
    context : str
        Human-readable location, interpolated into the error message.

    Returns
    -------
    Any
        ``d[key]``.

    Raises
    ------
    ReferenceLibraryError
        If ``key`` is not in ``d``.
    """
    if key not in d:
        raise ReferenceLibraryError(f"Missing required field '{key}' in {context}.")
    return d[key]


def _parse_analyte(name: str, raw: dict) -> ReferenceAnalyte:
    """Parse and validate one analyte entry from reference-material YAML.

    Parameters
    ----------
    name : str
        Analyte column name (the mapping key), used in error messages.
    raw : dict
        The analyte's YAML sub-mapping.

    Returns
    -------
    ReferenceAnalyte
        The validated entry. ``units`` defaults to ``"ppm"`` and
        ``uncertainty_type`` to ``"1SD"`` when ``value`` is unset.

    Raises
    ------
    ReferenceLibraryError
        If ``raw`` is not a mapping, ``element``/``mass`` are missing or
        malformed, a set ``value`` is non-numeric, or a set ``value`` lacks
        a valid ``uncertainty_type``.
    """
    context = f"analyte '{name}'"
    if not isinstance(raw, dict):
        raise ReferenceLibraryError(f"{context} must be a mapping, got {type(raw).__name__}.")

    element = _require(raw, "element", context)
    mass = _require(raw, "mass", context)
    try:
        mass = int(mass)
    except (TypeError, ValueError):
        raise ReferenceLibraryError(f"{context} 'mass' must be an integer, got {mass!r}.")

    value = raw.get("value")
    uncertainty = raw.get("uncertainty")
    uncertainty_type = raw.get("uncertainty_type")
    units = raw.get("units", "ppm")
    source = raw.get("source", "")

    if value is not None:
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ReferenceLibraryError(f"{context} 'value' must be numeric, got {value!r}.")
        # A populated value must carry an explicit, valid uncertainty type --
        # this is what lets a 'null' placeholder stay a legitimate, silent
        # state while a *populated* entry with no way to interpret its
        # uncertainty fails loudly instead of feeding a bogus number into the
        # accuracy z/t-test.
        if uncertainty_type not in VALID_UNCERTAINTY_TYPES:
            raise ReferenceLibraryError(
                f"{context} 'uncertainty_type' must be one of {sorted(VALID_UNCERTAINTY_TYPES)} "
                f"when 'value' is set, got {uncertainty_type!r}."
            )
    else:
        uncertainty_type = uncertainty_type or "1SD"

    if uncertainty is not None:
        try:
            uncertainty = float(uncertainty)
        except (TypeError, ValueError):
            raise ReferenceLibraryError(f"{context} 'uncertainty' must be numeric, got {uncertainty!r}.")

    return ReferenceAnalyte(
        element=str(element), mass=mass, value=value, uncertainty=uncertainty,
        uncertainty_type=uncertainty_type, units=units, source=str(source),
    )


def _parse_isotope_ratio(name: str, raw: dict) -> ReferenceIsotopeRatio:
    """Parse and validate one isotope-ratio entry from reference-material YAML.

    Parameters
    ----------
    name : str
        Ratio name (the mapping key), used in error messages.
    raw : dict
        The ratio's YAML sub-mapping.

    Returns
    -------
    ReferenceIsotopeRatio
        The validated entry; ``uncertainty_type`` may be ``None``.

    Raises
    ------
    ReferenceLibraryError
        If ``raw`` is not a mapping, the element/mass fields are missing or
        malformed, ``value``/``uncertainty`` are non-numeric, or
        ``uncertainty_type`` is set to something outside
        :data:`VALID_UNCERTAINTY_TYPES`.

    Warns
    -----
    UserWarning
        When ``value`` and ``uncertainty`` are both set but
        ``uncertainty_type`` is absent -- a real GeoREM data gap, surfaced
        rather than rejected.
    """
    context = f"isotope ratio '{name}'"
    if not isinstance(raw, dict):
        raise ReferenceLibraryError(f"{context} must be a mapping, got {type(raw).__name__}.")

    numerator_element = str(_require(raw, "numerator_element", context))
    denominator_element = str(_require(raw, "denominator_element", context))
    try:
        numerator_mass = int(_require(raw, "numerator_mass", context))
        denominator_mass = int(_require(raw, "denominator_mass", context))
    except (TypeError, ValueError):
        raise ReferenceLibraryError(f"{context} 'numerator_mass'/'denominator_mass' must be integers.")

    value = raw.get("value")
    if value is not None:
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ReferenceLibraryError(f"{context} 'value' must be numeric, got {value!r}.")

    uncertainty = raw.get("uncertainty")
    if uncertainty is not None:
        try:
            uncertainty = float(uncertainty)
        except (TypeError, ValueError):
            raise ReferenceLibraryError(f"{context} 'uncertainty' must be numeric, got {uncertainty!r}.")

    uncertainty_type = raw.get("uncertainty_type")
    if uncertainty_type is not None and uncertainty_type not in VALID_UNCERTAINTY_TYPES:
        raise ReferenceLibraryError(
            f"{context} 'uncertainty_type' must be one of {sorted(VALID_UNCERTAINTY_TYPES)} or null, "
            f"got {uncertainty_type!r}."
        )
    if value is not None and uncertainty is not None and uncertainty_type is None:
        # Unlike _parse_analyte, this is a warning, not a raise: some real
        # GeoREM rows (NIST612/614's isotope-ratio rows) genuinely report a
        # value and uncertainty with no stated uncertainty type at all --
        # this is a real data gap to surface, not a malformed file to reject.
        warnings.warn(
            f"{context} has a value/uncertainty but no uncertainty_type -- "
            "stored as uncertainty_type=None (uncertainty_1sd() will return None "
            "until this is resolved with a real source).", stacklevel=2,
        )

    return ReferenceIsotopeRatio(
        numerator_element=numerator_element, numerator_mass=numerator_mass,
        denominator_element=denominator_element, denominator_mass=denominator_mass,
        value=value, uncertainty=uncertainty, uncertainty_type=uncertainty_type,
        source=str(raw.get("source", "")),
    )


def parse_reference_material(raw: dict) -> ReferenceMaterial:
    """Build a :class:`ReferenceMaterial` from a parsed YAML mapping.

    Parameters
    ----------
    raw : dict
        The full YAML document as a mapping. Requires ``standard`` and a
        non-empty ``analytes`` mapping; ``description``, ``source``, and
        ``isotope_ratios`` are optional.

    Returns
    -------
    ReferenceMaterial
        The validated material. ``isotope_ratios`` is ``{}`` when the key
        is absent.

    Raises
    ------
    ReferenceLibraryError
        If the root or any sub-structure is not the expected shape, or a
        required field is missing (see :func:`_parse_analyte` and
        :func:`_parse_isotope_ratio`).
    """
    if not isinstance(raw, dict):
        raise ReferenceLibraryError(f"Config root must be a mapping, got {type(raw).__name__}.")

    standard = _require(raw, "standard", "config")
    description = raw.get("description", "")
    source = raw.get("source", "")

    analytes_raw = _require(raw, "analytes", "config")
    if not isinstance(analytes_raw, dict) or not analytes_raw:
        raise ReferenceLibraryError("'analytes' must be a non-empty mapping of column name -> analyte config.")
    analytes = {name: _parse_analyte(name, a) for name, a in analytes_raw.items()}

    # Optional, not _require'd -- every existing concentration-only YAML
    # file (including _template.yaml) has no 'isotope_ratios' key and must
    # keep loading unchanged, with isotope_ratios == {}.
    ratios_raw = raw.get("isotope_ratios", {}) or {}
    if not isinstance(ratios_raw, dict):
        raise ReferenceLibraryError("'isotope_ratios', if present, must be a mapping of ratio name -> config.")
    isotope_ratios = {name: _parse_isotope_ratio(name, r) for name, r in ratios_raw.items()}

    return ReferenceMaterial(
        standard=str(standard), description=str(description), source=str(source),
        analytes=analytes, isotope_ratios=isotope_ratios,
    )


def load_reference_material(path: str | Path) -> ReferenceMaterial:
    """Load and validate a single reference-material YAML file.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the YAML file.

    Returns
    -------
    ReferenceMaterial
        The parsed and validated material.

    Raises
    ------
    ReferenceLibraryError
        If the YAML cannot be parsed, the file is empty, or validation
        fails (see :func:`parse_reference_material`).
    """
    path = Path(path)
    try:
        with path.open("r") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ReferenceLibraryError(f"Could not parse YAML in {path}: {e}") from e
    if raw is None:
        raise ReferenceLibraryError(f"{path} is empty.")
    return parse_reference_material(raw)


def load_reference_library(dir_path: str | Path) -> dict[str, ReferenceMaterial]:
    """Load every reference-material YAML in a directory.

    Parameters
    ----------
    dir_path : str or pathlib.Path
        Directory to scan (non-recursively) for ``*.yaml`` files. Files
        whose stem starts with ``_`` (e.g. ``_template.yaml``) are skipped.

    Returns
    -------
    dict[str, ReferenceMaterial]
        Loaded materials keyed by their ``standard`` name.

    Raises
    ------
    ReferenceLibraryError
        If any loaded file fails to parse or validate.
    """
    dir_path = Path(dir_path)
    library: dict[str, ReferenceMaterial] = {}
    for path in sorted(dir_path.glob("*.yaml")):
        if path.stem.startswith("_"):
            continue
        material = load_reference_material(path)
        library[material.standard] = material
    return library


def save_reference_material(material: ReferenceMaterial, path: str | Path) -> None:
    """Write a :class:`ReferenceMaterial` back out as YAML.

    Parameters
    ----------
    material : ReferenceMaterial
        The material to serialize.
    path : str or pathlib.Path
        Destination YAML path (overwritten if it exists).

    Returns
    -------
    None

    Notes
    -----
    Field order is preserved (``sort_keys=False``). Backs the GUI's
    "Edit standard" dialog.
    """
    raw = {
        "standard": material.standard,
        "description": material.description,
        "source": material.source,
        "analytes": {
            name: {
                "element": a.element,
                "mass": a.mass,
                "value": a.value,
                "uncertainty": a.uncertainty,
                "uncertainty_type": a.uncertainty_type,
                "units": a.units,
                "source": a.source,
            }
            for name, a in material.analytes.items()
        },
        "isotope_ratios": {
            name: {
                "numerator_element": r.numerator_element,
                "numerator_mass": r.numerator_mass,
                "denominator_element": r.denominator_element,
                "denominator_mass": r.denominator_mass,
                "value": r.value,
                "uncertainty": r.uncertainty,
                "uncertainty_type": r.uncertainty_type,
                "source": r.source,
            }
            for name, r in material.isotope_ratios.items()
        },
    }
    path = Path(path)
    with path.open("w") as f:
        yaml.safe_dump(raw, f, sort_keys=False)
