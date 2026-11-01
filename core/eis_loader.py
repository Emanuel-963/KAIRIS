"""BT-Lab EIS loading, circuit-free quality checks and morphology features."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any
import unicodedata

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ("freq/Hz", "Re(Z)/Ohm", "-Im(Z)/Ohm")

_COLUMN_ALIASES = {
    "frequency": {
        "freq/hz",
        "frequency(hz)",
        "frequency/hz",
        "frequency_hz",
        "f(hz)",
    },
    "real": {
        "re(z)/ohm",
        "re(z)(ohm)",
        "z'(ohm)",
        "zre(ohm)",
        "real_ohm",
    },
    "negative_imaginary": {
        "-im(z)/ohm",
        "-im(z)(ohm)",
        "-z''(ohm)",
        "-zim(ohm)",
        "negativeimaginary_ohm",
    },
    "imaginary": {
        "im(z)/ohm",
        "im(z)(ohm)",
        "z''(ohm)",
        "zim(ohm)",
        "imag_ohm",
    },
}


def _column_key(value: Any) -> str:
    """Normalize equivalent EIS column labels from supported instruments."""
    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    text = text.replace("ω", "ohm").replace("Ω", "ohm")
    text = text.replace("î©", "ohm")
    text = text.replace("′", "'").replace("″", "''")
    text = re.sub(r"\s+", "", text)
    return text


def _resolve_columns(columns: list[Any]) -> dict[str, Any] | None:
    """Map source-specific labels to the three impedance quantities."""
    resolved: dict[str, Any] = {}
    for column in columns:
        key = _column_key(column)
        for quantity, aliases in _COLUMN_ALIASES.items():
            if key in aliases and quantity not in resolved:
                resolved[quantity] = column
    required = {"frequency", "real"}
    has_imaginary = "negative_imaginary" in resolved or "imaginary" in resolved
    return resolved if required.issubset(resolved) and has_imaginary else None


def _detect_layout(path: Path, config: dict[str, Any]) -> tuple[str, str, int]:
    """Detect text encoding, field separator and EIS header line."""
    raw = path.read_bytes()
    configured_encoding = str(config.get("btlab_encoding", "latin-1"))
    encodings = list(dict.fromkeys(("utf-8-sig", "utf-8", configured_encoding, "latin-1")))
    configured_separator = str(config.get("btlab_separator", "\t"))
    separators = list(dict.fromkeys((configured_separator, "\t", ";", ",")))

    for encoding in encodings:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(text.splitlines()):
            for separator in separators:
                if separator in line and _resolve_columns(line.split(separator)):
                    return encoding, separator, index

    expected = "frequência, parte real e parte imaginária negativa"
    raise ValueError(
        f"Cabeçalho EIS compatível não encontrado em {path.name}; "
        f"esperadas colunas de {expected}."
    )


def _to_numeric(series: pd.Series, decimal: str) -> pd.Series:
    """Parse decimal-comma scientific notation independently of pandas version."""
    values = series.astype("string").str.strip().str.replace("−", "-", regex=False)
    if decimal and decimal != ".":
        values = values.str.replace(decimal, ".", regex=False)
    return pd.to_numeric(values, errors="coerce")


def load_btlab(filepath: str | Path, config: dict[str, Any]) -> dict[str, np.ndarray]:
    """Load and sanitize a supported EIS text export for KAIRIS.

    Tab-separated and semicolon-separated TXT/CSV exports are detected
    automatically. Frequencies are returned from high to low. Columns named
    ``-Im(Z)`` or ``-Z''`` are negated, while a signed ``Z''``/``Im(Z)`` column
    is preserved as supplied.
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(path)
    encoding, separator, header = _detect_layout(path, config)
    decimal = str(config.get("btlab_decimal", ","))
    frame = pd.read_csv(
        path,
        sep=separator,
        decimal=decimal,
        encoding=encoding,
        skiprows=header,
        engine="python",
    )
    frame.columns = [str(column).strip() for column in frame.columns]
    columns = _resolve_columns(frame.columns.tolist())
    if columns is None:
        raise ValueError(f"Não foi possível mapear as colunas EIS em {path.name}.")

    if "negative_imaginary" in columns:
        imaginary = -_to_numeric(frame[columns["negative_imaginary"]], decimal)
    else:
        # Headers such as Z'' contain the signed imaginary component directly.
        imaginary = _to_numeric(frame[columns["imaginary"]], decimal)
    selected = pd.DataFrame(
        {
            "frequency": _to_numeric(frame[columns["frequency"]], decimal),
            "real": _to_numeric(frame[columns["real"]], decimal),
            "imaginary": imaginary,
        }
    )
    selected = selected.dropna()
    selected = selected[selected["frequency"] > 0]
    selected = selected.drop_duplicates(subset="frequency", keep="first")
    selected = selected.sort_values("frequency", ascending=False)
    if selected.empty:
        raise ValueError(f"Nenhum ponto EIS numérico válido em {path.name}")

    return {
        "frequency": selected["frequency"].to_numpy(dtype=float),
        "real": selected["real"].to_numpy(dtype=float),
        "imag": selected["imaginary"].to_numpy(dtype=float),
    }


def validate_spectral_smoothness(
    frequency: np.ndarray,
    real: np.ndarray,
    imag: np.ndarray,
    strict_threshold: float = 0.05,
    permissive_threshold: float = 0.15,
) -> dict[str, Any]:
    """Evaluate local complex-gradient smoothness without fitting a circuit.

    Each interior impedance is reconstructed from its two neighbours by linear
    interpolation in log-frequency.  The normalized complex residual is a
    deterministic local-residue smoothness indicator. Endpoints use a one-sided
    linear extrapolation. This is not an integral Kramers-Kronig validation.
    """
    frequency = np.asarray(frequency, dtype=float)
    z = np.asarray(real, dtype=float) + 1j * np.asarray(imag, dtype=float)
    n = z.size
    residual = np.full(n, np.inf, dtype=float)
    if n >= 3:
        x = np.log(frequency)
        for index in range(n):
            if index == 0:
                support = (1, 2)
            elif index == n - 1:
                support = (n - 3, n - 2)
            else:
                support = (index - 1, index + 1)
            i0, i1 = support
            span = x[i1] - x[i0]
            if np.isclose(span, 0.0):
                continue
            weight = (x[index] - x[i0]) / span
            estimate = z[i0] + weight * (z[i1] - z[i0])
            scale = max(abs(z[index]), np.median(np.abs(z)), np.finfo(float).eps)
            residual[index] = abs(z[index] - estimate) / scale

    smoothness_pass_strict = np.isfinite(residual) & (residual <= strict_threshold)
    smoothness_pass_permissive = np.isfinite(residual) & (residual <= permissive_threshold)
    n_strict_fail = int(np.count_nonzero(~smoothness_pass_strict))
    n_permissive_fail = int(np.count_nonzero(~smoothness_pass_permissive))
    return {
        "residual": residual,
        "smoothness_pass_strict": smoothness_pass_strict,
        "smoothness_pass_permissive": smoothness_pass_permissive,
        "n_total": int(n),
        "smoothness_failures_strict": n_strict_fail,
        "smoothness_failures_permissive": n_permissive_fail,
        "smoothness_residue_pct": 100.0 * n_strict_fail / max(n, 1),
    }


def classify_morphology(real: np.ndarray, imag: np.ndarray) -> str:
    """Classify broad Nyquist morphology using transparent geometric rules."""
    real = np.asarray(real, dtype=float)
    y = np.abs(np.asarray(imag, dtype=float))
    n = real.size
    if n < 5 or np.ptp(real) <= np.finfo(float).eps:
        return "unknown"

    peak = int(np.argmax(y))
    interior_peak = 0 < peak < n - 1
    end_level = max(y[0], y[-1], np.finfo(float).eps)
    arc = interior_peak and y[peak] >= 1.25 * end_level

    tail_count = max(3, int(np.ceil(0.3 * n)))
    x_tail = real[-tail_count:]
    y_tail = y[-tail_count:]
    if np.ptp(x_tail) > np.finfo(float).eps:
        slope = abs(float(np.polyfit(x_tail, y_tail, 1)[0]))
        correlation = abs(float(np.corrcoef(x_tail, y_tail)[0, 1]))
        diffusive = 0.5 <= slope <= 1.5 and correlation >= 0.8
    else:
        diffusive = False

    if arc and diffusive:
        return "mixed"
    if arc:
        return "capacitive_arc"
    if diffusive:
        return "diffusive_tail"
    return "unknown"


def json_safe_z_data(data: dict[str, np.ndarray]) -> dict[str, list[float]]:
    """Convert numerical arrays to a JSON-friendly spectral payload."""
    return {key: np.asarray(value).astype(float).tolist() for key, value in data.items()}

