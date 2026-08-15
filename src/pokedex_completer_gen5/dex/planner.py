from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from pokedex_completer_gen5.dex.action_data import action_hint_for_national
from pokedex_completer_gen5.dex.breeding import breeding_rule_for_family
from pokedex_completer_gen5.dex.bw_unova import BY_NAME, BY_NATIONAL, BY_REGIONAL, UNOVA_DEX, Pokemon


@dataclass(frozen=True)
class DexStatus:
    owned: tuple[Pokemon, ...]
    missing: tuple[Pokemon, ...]
    unknown_tokens: tuple[str, ...]
    owned_counts: tuple[tuple[int, int], ...]

    def count_for(self, pokemon: Pokemon) -> int:
        return dict(self.owned_counts).get(pokemon.regional, 0)


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'. -]*|#?\d+")


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


NORMALIZED_NAME_INDEX = {normalize_name(name): pokemon for name, pokemon in BY_NAME.items()}


def parse_owned_text(text: str, number_mode: str = "regional") -> DexStatus:
    """Parse owned Pokémon from casual text.

    Accepts names, regional numbers, national numbers, comma/newline lists, and '#025'-style tokens.
    For Black/White, regional numbers are usually what the in-game Pokédex shows.
    """
    owned: dict[int, Pokemon] = {}
    counts: dict[int, int] = defaultdict(int)
    unknown: list[str] = []

    for raw in TOKEN_RE.findall(text):
        token = raw.strip().strip(",;:")
        if not token:
            continue

        pokemon = parse_token(token, number_mode)
        if pokemon is None:
            # Ignore tiny connector words from prose. This is a parser, not a toddler with a net.
            if len(token) > 2:
                unknown.append(token)
            continue
        owned[pokemon.regional] = pokemon
        counts[pokemon.regional] += 1

    owned_tuple = tuple(sorted(owned.values(), key=lambda p: p.regional))
    owned_counts = tuple(sorted(counts.items()))
    missing = tuple(pokemon for pokemon in UNOVA_DEX if pokemon.regional not in owned)
    return DexStatus(
        owned=owned_tuple,
        missing=missing,
        unknown_tokens=tuple(unknown),
        owned_counts=owned_counts,
    )


def parse_token(token: str, number_mode: str) -> Pokemon | None:
    cleaned = token.removeprefix("#")
    if cleaned.isdigit():
        number = int(cleaned)
        if number_mode == "national":
            return BY_NATIONAL.get(number)
        if number_mode == "auto":
            return BY_REGIONAL.get(number) or BY_NATIONAL.get(number)
        return BY_REGIONAL.get(number)

    return NORMALIZED_NAME_INDEX.get(normalize_name(token))


def classify(pokemon: Pokemon, game: str) -> str:
    if pokemon.event_only:
        return "event"
    if game == "black" and pokemon.white_only:
        return "trade/version-exclusive"
    if game == "white" and pokemon.black_only:
        return "trade/version-exclusive"
    if "trade evolve" in pokemon.method or pokemon.method.startswith("trade "):
        return "trade-evolution"
    if "evolve" in pokemon.method or "Stone" in pokemon.method or "friendship" in pokemon.method:
        return "evolution"
    if "legendary" in pokemon.method or "roamer" in pokemon.method:
        return "legendary"
    return "catchable"


def build_plan(status: DexStatus, game: str) -> dict[str, list[Pokemon]]:
    buckets: dict[str, list[Pokemon]] = defaultdict(list)
    for pokemon in status.missing:
        buckets[classify(pokemon, game)].append(pokemon)
    return dict(sorted(buckets.items()))


@dataclass(frozen=True)
class FamilyLivingDexPlan:
    family: tuple[Pokemon, ...]
    missing: tuple[Pokemon, ...]
    owned_body_count: int

    @property
    def base(self) -> Pokemon:
        return self.family[0]

    @property
    def additional_bodies_needed(self) -> int:
        return max(0, len(self.family) - self.owned_body_count)


def family_plan(status: DexStatus) -> list[FamilyLivingDexPlan]:
    plans: dict[tuple[str, ...], FamilyLivingDexPlan] = {}
    missing_by_family: dict[tuple[str, ...], list[Pokemon]] = defaultdict(list)

    for pokemon in status.missing:
        missing_by_family[pokemon.family].append(pokemon)

    for family_names, missing in missing_by_family.items():
        family = tuple(BY_NAME[name.casefold()] for name in family_names)
        owned_body_count = sum(status.count_for(pokemon) for pokemon in family)
        plans[family_names] = FamilyLivingDexPlan(
            family=family,
            missing=tuple(sorted(missing, key=lambda p: p.regional)),
            owned_body_count=owned_body_count,
        )

    return sorted(plans.values(), key=lambda plan: plan.family[0].regional)


@dataclass(frozen=True)
class BreedingShortcut:
    plan: FamilyLivingDexPlan
    eggs_needed: int
    note: str


def breeding_shortcuts(status: DexStatus) -> list[BreedingShortcut]:
    shortcuts: list[BreedingShortcut] = []
    for plan in family_plan(status):
        if not plan.missing:
            continue
        if plan.owned_body_count <= 0:
            continue
        if plan.additional_bodies_needed <= 0:
            continue
        rule = breeding_rule_for_family(tuple(pokemon.national for pokemon in plan.family))
        if not rule.can_breed:
            continue
        shortcuts.append(
            BreedingShortcut(
                plan=plan,
                eggs_needed=plan.additional_bodies_needed,
                note=rule.note,
            )
        )
    return shortcuts


def format_pokemon(pokemon: Pokemon) -> str:
    return f"#{pokemon.regional:03d} {pokemon.name} (Nat #{pokemon.national}) — {pokemon.method}"


def render_report(status: DexStatus, game: str) -> str:
    lines: list[str] = []
    total = len(UNOVA_DEX)
    total_bodies_listed = sum(count for _, count in status.owned_counts)
    lines.append(f"Game: Pokémon {game.title()}")
    lines.append("Mode: Living Dex — one physical Pokémon for every regional dex stage")
    lines.append(f"Unique species owned: {len(status.owned)} / {total}")
    lines.append(f"Owned bodies listed: {total_bodies_listed}")
    lines.append(f"Missing living dex species: {len(status.missing)} / {total}")
    lines.append("")

    if status.unknown_tokens:
        lines.append("Unknown tokens ignored:")
        lines.append("  " + ", ".join(status.unknown_tokens[:30]))
        if len(status.unknown_tokens) > 30:
            lines.append(f"  ...and {len(status.unknown_tokens) - 30} more")
        lines.append("")

    lines.append("Priority buckets:")
    for bucket, pokemon_list in build_plan(status, game).items():
        lines.append(f"\n[{bucket}] {len(pokemon_list)}")
        for pokemon in pokemon_list:
            lines.append("  " + format_pokemon(pokemon))

    shortcuts = breeding_shortcuts(status)
    if shortcuts:
        lines.append("\nBreeding shortcuts:")
        lines.append("  If you already have a breedable family member, breed base-stage extras first.")
        lines.append("  Then evolve only the extras. Do not evolve your last copy like a gremlin.")
        for shortcut in shortcuts:
            plan = shortcut.plan
            missing_names = ", ".join(pokemon.name for pokemon in plan.missing)
            lines.append(
                f"  {plan.base.name} line: breed {shortcut.eggs_needed} extra "
                f"{plan.base.name} egg(s) to cover missing: {missing_names} "
                f"({shortcut.note})"
            )

    lines.append("\nLiving Dex family checklist:")
    for plan in family_plan(status):
        family_names = " / ".join(pokemon.name for pokemon in plan.family)
        missing_names = ", ".join(f"#{p.regional:03d} {p.name}" for p in plan.missing)
        lines.append(
            f"  {family_names} -> missing species: {missing_names}; "
            f"owned family bodies: {plan.owned_body_count}/{len(plan.family)}; "
            f"additional bodies needed: {plan.additional_bodies_needed}"
        )
        hint = action_hint_for_national(plan.base.national)
        if hint is not None:
            lines.append(f"    acquire: {hint.acquire}")
            if hint.evolve:
                lines.append(f"    evolve: {hint.evolve}")
            if hint.item:
                lines.append(f"    item: {hint.item}")
            if hint.caveat:
                lines.append(f"    caveat: {hint.caveat}")

    return "\n".join(lines) + "\n"
