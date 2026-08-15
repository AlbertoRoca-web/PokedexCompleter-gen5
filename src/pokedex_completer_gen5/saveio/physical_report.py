from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pokedex_completer_gen5.dex.bw_unova import BY_NATIONAL, Pokemon
from pokedex_completer_gen5.dex.game_profiles import normalize_game
from pokedex_completer_gen5.dex.national_species import national_species_name
from pokedex_completer_gen5.dex.planner import DexStatus, render_report
from pokedex_completer_gen5.saveio.active_copy import choose_copy
from pokedex_completer_gen5.saveio.gen5_reader import PhysicalMon, SaveCopyReport, read_save_copy


def species_name(species_id: int) -> str:
    return national_species_name(species_id)


def status_from_counts(counts: Counter[int]) -> DexStatus:
    unova_counts: dict[int, int] = {}
    owned: dict[int, Pokemon] = {}
    for national_id, count in counts.items():
        pokemon = BY_NATIONAL.get(national_id)
        if pokemon is None:
            continue
        owned[pokemon.regional] = pokemon
        unova_counts[pokemon.regional] = count

    missing = tuple(pokemon for pokemon in BY_NATIONAL.values() if pokemon.regional not in owned)
    return DexStatus(
        owned=tuple(sorted(owned.values(), key=lambda p: p.regional)),
        missing=tuple(sorted(missing, key=lambda p: p.regional)),
        unknown_tokens=tuple(),
        owned_counts=tuple(sorted(unova_counts.items())),
    )


def render_physical_summary(report: SaveCopyReport) -> str:
    lines: list[str] = []
    lines.append(f"Save copy {report.copy_index} at 0x{report.copy_base:05X}")
    lines.append(f"Party count hint: {report.party_count_hint}")
    lines.append(f"Physical mons decoded: {len(report.mons)}")
    for mon in report.mons:
        lines.append(
            f"  {mon.source.upper():5s} {mon.slot_label:16s} "
            f"{species_name(mon.species_id)} ({mon.species_id:03d}) "
            f"pid=0x{mon.pid:08X} checksum=0x{mon.checksum:04X}"
        )
    lines.append("Species body counts:")
    for species_id, count in sorted(report.counts.items()):
        lines.append(f"  {species_id:03d}\t{count}\t{species_name(species_id)}")
    return "\n".join(lines)


def physical_mon_to_dict(mon: PhysicalMon) -> dict[str, object]:
    return {
        "species_id": mon.species_id,
        "species_name": species_name(mon.species_id),
        "source": mon.source,
        "slot_label": mon.slot_label,
        "pid": mon.pid,
        "pid_hex": f"0x{mon.pid:08X}",
        "checksum": mon.checksum,
        "checksum_hex": f"0x{mon.checksum:04X}",
    }


def copy_report_to_dict(report: SaveCopyReport) -> dict[str, object]:
    return {
        "copy_index": report.copy_index,
        "copy_base": report.copy_base,
        "copy_base_hex": f"0x{report.copy_base:05X}",
        "party_count_hint": report.party_count_hint,
        "physical_mons_decoded": len(report.mons),
        "mons": [physical_mon_to_dict(mon) for mon in report.mons],
        "species_counts": [
            {"species_id": species_id, "species_name": species_name(species_id), "count": count}
            for species_id, count in sorted(report.counts.items())
        ],
    }


def dex_status_to_dict(status: DexStatus) -> dict[str, object]:
    return {
        "unique_species_owned": len(status.owned),
        "missing_species_count": len(status.missing),
        "owned": [
            {"regional": pokemon.regional, "national": pokemon.national, "name": pokemon.name}
            for pokemon in status.owned
        ],
        "missing": [
            {"regional": pokemon.regional, "national": pokemon.national, "name": pokemon.name}
            for pokemon in status.missing
        ],
        "owned_counts": [
            {"regional": regional, "count": count} for regional, count in status.owned_counts
        ],
    }


def build_save_payload(save_path: Path, game: str, requested_copy: str = "auto") -> dict[str, object]:
    profile = normalize_game(game)
    data = save_path.read_bytes()
    reports = [read_save_copy(data, 0), read_save_copy(data, 1)]
    selected = choose_copy(reports, requested_copy)
    same_counts = reports[0].counts == reports[1].counts
    status = status_from_counts(selected.counts) if profile.planner_supported else None
    return {
        "save": str(save_path),
        "size": len(data),
        "mode": "read-only",
        "requested_copy": requested_copy,
        "selected_copy": selected.copy_index,
        "copy_counts_match": same_counts,
        "game_profile": profile.key,
        "regional_dex_key": profile.regional_dex_key,
        "planner_supported": profile.planner_supported,
        "planner_notes": profile.notes,
        "copies": [copy_report_to_dict(report) for report in reports],
        "selected_species_counts": [
            {"species_id": species_id, "species_name": species_name(species_id), "count": count}
            for species_id, count in sorted(selected.counts.items())
        ],
        "dex_status": dex_status_to_dict(status) if status is not None else None,
    }


def build_save_report(save_path: Path, game: str, requested_copy: str = "auto") -> str:
    profile = normalize_game(game)
    data = save_path.read_bytes()
    reports = [read_save_copy(data, 0), read_save_copy(data, 1)]
    selected = choose_copy(reports, requested_copy)

    same_counts = reports[0].counts == reports[1].counts
    lines: list[str] = []
    lines.append(f"save={save_path}")
    lines.append(f"size={len(data)}")
    lines.append("mode=read-only")
    lines.append(f"requested_copy={requested_copy}")
    lines.append(f"selected_copy={selected.copy_index}")
    lines.append(f"copy_counts_match={same_counts}")
    lines.append(f"game_profile={profile.key}")
    lines.append(f"regional_dex_key={profile.regional_dex_key}")
    lines.append("")
    for report in reports:
        lines.append(render_physical_summary(report))
        lines.append("")

    if profile.planner_supported:
        lines.append("Unova Living Dex Plan From Selected Physical Bodies")
        lines.append("===================================================")
        lines.append(render_report(status_from_counts(selected.counts), game=profile.key))
    else:
        lines.append("Regional Living Dex Plan")
        lines.append("========================")
        lines.append(f"{profile.title} is recognized and physical extraction worked.")
        lines.append(profile.notes)
        lines.append("No regional living dex plan was generated because B2W2 has a different regional dex.")
        lines.append("This is intentional: refusing to silently use the wrong BW Unova checklist.")

    return "\n".join(lines) + "\n"


def default_report_path(save_path: Path, game: str) -> Path:
    profile = normalize_game(game)
    return save_path.with_name(save_path.stem + f"-{profile.key}-living-dex-report.txt")


def build_save_output(
    save_path: Path,
    game: str,
    requested_copy: str = "auto",
    output_format: str = "markdown",
) -> str:
    if output_format == "json":
        return json.dumps(build_save_payload(save_path, game, requested_copy), indent=2) + "\n"
    if output_format == "markdown":
        return build_save_report(save_path, game, requested_copy)
    raise ValueError(f"Unsupported output format: {output_format}")


def write_save_report(
    save_path: Path,
    game: str,
    requested_copy: str = "auto",
    output: Path | None = None,
    output_format: str = "markdown",
) -> tuple[Path, str]:
    report = build_save_output(save_path, game, requested_copy, output_format)
    output_path = output or default_report_path(save_path, game)
    output_path.write_text(report, encoding="utf-8")
    return output_path, report
