from __future__ import annotations

from pokedex_completer_gen5.saveio.gen5_reader import SaveCopyReport


def choose_copy(reports: list[SaveCopyReport], requested: str) -> SaveCopyReport:
    if requested in ("0", "1"):
        return reports[int(requested)]
    if reports[0].counts == reports[1].counts:
        return reports[0]
    return max(
        reports,
        key=lambda report: (
            len(report.mons),
            sum(report.counts.values()),
            report.party_count_hint,
        ),
    )
