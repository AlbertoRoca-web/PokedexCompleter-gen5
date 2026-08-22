# Pokémon White Route 1 Encounter Completion

Last updated: 2026-08-22

Scope: original Pokémon White, Generation V. Do not mix with Black 2/White 2 tables.

## Completion Rule

A route is not complete merely because ordinary grass encounters are owned. Completion must be tracked by encounter method and access condition:

```text
ordinary grass
+ shaking/rustling grass
+ dark/double grass
+ normal Surf
+ rippling Surf
+ ordinary Super Rod
+ rippling-water Super Rod
+ daily swarm
```

A target may be marked deferred when its phenomenon, access prerequisite, or daily condition cannot yet be detected safely. Deferred is not complete.

## Verified Encounter Table

| Species | Form in White | Method/tile | Levels | Chance | Access/notes |
| --- | --- | --- | --- | ---: | --- |
| Patrat | — | ordinary grass | 2–4 | 50% | Initial route area. Caught. |
| Lillipup | — | ordinary grass | 2–4 | 50% | Initial route area. Two physical bodies owned. |
| Audino | — | shaking/rustling grass | 2–4 | 100% | Must enter an active shaking grass tile. Deferred until detection is reliable. |
| Herdier | — | dark/double grass | 32–34 | 39% | Western post-Surf area. Two Lillipup bodies cover retained Lillipup plus future Herdier; a third family body is still required for Stoutland. |
| Watchog | — | dark/double grass | 32–35 | 36% | Western post-Surf area. Two Patrat bodies can cover Patrat plus Watchog. |
| Scraggy | — | dark/double grass | 33–35 | 25% | Western post-Surf area. Still required. |
| Basculin | Blue-Striped | normal Surf | 5–15 | 100% | White's ordinary-water form. Physical Basculin already owned. |
| Basculin | Red-Striped | rippling Surf | 5–20 | 100% | Enter an active ripple while Surfing. Form tracking is separate from species-body completion. |
| Basculin | Blue-Striped | ordinary Super Rod | 35–55 | 95% | Physical level-36 female caught at verified east-bank pond landing. |
| Feebas | — | ordinary Super Rod | 35–55 | **5%** | No ripple required. Current best Route 1 target. |
| Feebas | — | rippling-water Super Rod | 35–60 | **60%** | Cast specifically into an active ripple. |
| Basculin | Red-Striped | rippling-water Super Rod | 35–70 | **35%** | White's special-water form. |
| Milotic | — | rippling-water Super Rod | 45–70 | **5%** | Cannot appear from ordinary non-rippling fishing. |
| Farfetch'd | — | swarm grass | 15–55 | 40% | Only when Route 1 is the current daily swarm. |

There are no seasonal encounter-table changes for these original Black/White Route 1 encounters.

## Fishing Tile Rules

- Ordinary shore fishing requires a fishable adjacent water tile and the Super Rod; Surf is not inherently required.
- Not every decorative water edge is a valid casting position.
- The rectangular pond's east bank beside the red-railed stair passage is a supervised, verified fishing landing.
- Ordinary water uses the 95% Basculin / 5% Feebas table.
- Special fishing requires an active visible ripple and a cast into that exact tile.
- Fishing elsewhere in the same pond while a ripple exists does not use the ripple table.
- Rippling Surf requires physically entering the active ripple while Surfing.

## Current Route 1 State

Physically verified in party/PC save extraction:

- Patrat;
- Lillipup family reserve bodies;
- Basculin in Box 01 Slot 20.

Next target:

```text
Feebas -> ordinary Super Rod -> verified pond east bank -> 5%
```

Expected mean attempts for an independent 5% encounter is 20 casts. Use a bounded retry batch, checkpoint first, and inspect every encounter. Flee from duplicate Basculin safely; catch Feebas when encountered.

Deferred Route 1 work:

- Audino until shaking-grass detection is reliable;
- Milotic and high-rate Feebas until ripple detection/casting is reliable;
- western dark grass until Surf navigation is verified;
- Farfetch'd until daily swarm state is confirmed.

## Sources

- Serebii Pokéarth, Unova Route 1: https://www.serebii.net/pokearth/unova/route1.shtml
- Bulbapedia, Unova Route 1: https://bulbapedia.bulbagarden.net/wiki/Unova_Route_1
- PokéAPI location area 623: https://pokeapi.co/api/v2/location-area/623/
- Pokémon Database, Unova Route 1: https://pokemondb.net/location/unova-route-1

PokéAPI splits some displayed encounter probabilities across internal slots. Aggregate by version, form, and method:

- ordinary Feebas: 4% + 1% = 5%;
- rippling Milotic: 4% + 1% = 5%;
- rippling Feebas total = 60%;
- rippling Basculin total = 35%.
