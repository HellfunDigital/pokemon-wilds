"""Tools for building and managing custom Pokemon gyms.

The module implements a small simulation layer that lets players design a
specialised Pokemon gym.  Gyms must focus on a single Pokemon type and can only
include Pokemon of that type.  Two exceptions are allowed as long as the Pokemon
learn the gym's signature move.  The module provides the following main
concepts:

* :class:`Pokemon` – stores a Pokemon's typing and moveset.
* :class:`Trainer` – represents a gym trainer and the Pokemon on their team.
* :class:`Room` – lightweight descriptor for rooms or facilities inside the gym.
* :class:`Gym` – validates trainers and Pokemon against the specialty rules and
  keeps track of the gym layout.
* :class:`GymBuilder` – convenience class that orchestrates the building flow.

Even though the real game logic is not part of this repository, the API offered
here can be imported into other tooling or used on the command line / tests to
experiment with different gym layouts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set


def _normalise_type(pokemon_type: str) -> str:
    """Normalise Pokemon type names to a canonical title-case representation."""

    return pokemon_type.strip().title()


def _normalise_move(move: str) -> str:
    """Normalise move names for comparisons."""

    return move.strip().lower()


@dataclass
class Pokemon:
    """Representation of a Pokemon's battle relevant information."""

    name: str
    types: Set[str]
    moves: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.types = {_normalise_type(p_type) for p_type in self.types}
        self.moves = {_normalise_move(move) for move in self.moves}

    def learn_move(self, move: str) -> None:
        """Teach the Pokemon a new move."""

        self.moves.add(_normalise_move(move))

    def knows_move(self, move: str) -> bool:
        """Return whether the Pokemon knows the supplied move."""

        return _normalise_move(move) in self.moves


@dataclass
class Trainer:
    """Stores the name and team for a trainer within a gym."""

    name: str
    team: List[Pokemon] = field(default_factory=list)
    title: Optional[str] = None

    def describe(self) -> str:
        """Return a short textual description of the trainer and their team."""

        role = f" ({self.title})" if self.title else ""
        pokemon_names = ", ".join(pokemon.name for pokemon in self.team) or "No Pokemon"
        return f"{self.name}{role}: {pokemon_names}"


@dataclass
class Room:
    """Lightweight representation of a room in a gym."""

    name: str
    purpose: str
    decorations: Sequence[str] = field(default_factory=list)

    def describe(self) -> str:
        decorations = ", ".join(self.decorations) if self.decorations else "None"
        return f"{self.name} – {self.purpose}. Decorations: {decorations}."


class Gym:
    """A Pokemon gym specialising in a single type."""

    def __init__(
        self,
        name: str,
        specialty_type: str,
        signature_move: str,
        *,
        max_off_type: int = 2,
    ) -> None:
        if max_off_type < 0:
            raise ValueError("max_off_type must be non-negative")

        self.name = name
        self.specialty_type = _normalise_type(specialty_type)
        self.signature_move = _normalise_move(signature_move)
        self.max_off_type = max_off_type
        self.rooms: Dict[str, Room] = {}
        self.trainers: List[Trainer] = []
        self.leader: Optional[Trainer] = None

    # ------------------------------------------------------------------
    # Helpers and derived information
    # ------------------------------------------------------------------
    @property
    def _all_trainers(self) -> Iterable[Trainer]:
        if self.leader is not None:
            yield self.leader
        yield from self.trainers

    @property
    def off_type_count(self) -> int:
        """Return the number of off-type Pokemon currently registered."""

        return sum(
            1
            for trainer in self._all_trainers
            for pokemon in trainer.team
            if not self.is_specialist(pokemon)
        )

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def is_specialist(self, pokemon: Pokemon) -> bool:
        """Return whether a Pokemon shares the gym's specialty type."""

        return self.specialty_type in pokemon.types

    def _ensure_pokemon_allowed(self, pokemon: Pokemon) -> None:
        if self.is_specialist(pokemon):
            return
        if not pokemon.knows_move(self.signature_move):
            raise ValueError(
                f"{pokemon.name} must know {self.signature_move.title()} to participate"
            )

    def _check_off_type_quota(self, additional_off_type: int) -> None:
        if self.off_type_count + additional_off_type > self.max_off_type:
            raise ValueError(
                "Gym already has the maximum number of off-type Pokemon"
            )

    def _count_off_type_in_team(self, team: Sequence[Pokemon]) -> int:
        return sum(1 for pokemon in team if not self.is_specialist(pokemon))

    def _validate_team(self, team: Sequence[Pokemon]) -> None:
        off_type_to_add = self._count_off_type_in_team(team)
        for pokemon in team:
            self._ensure_pokemon_allowed(pokemon)
        self._check_off_type_quota(off_type_to_add)

    # ------------------------------------------------------------------
    # Room management
    # ------------------------------------------------------------------
    def build_room(
        self,
        room_name: str,
        *,
        purpose: str,
        decorations: Optional[Sequence[str]] = None,
    ) -> None:
        """Add a new room to the gym."""

        key = room_name.lower()
        if key in self.rooms:
            raise ValueError(f"Room '{room_name}' already exists")
        self.rooms[key] = Room(room_name, purpose, tuple(decorations or ()))

    def describe_rooms(self) -> List[str]:
        """Return human readable descriptions for all rooms."""

        return [room.describe() for room in self.rooms.values()]

    # ------------------------------------------------------------------
    # Trainer management
    # ------------------------------------------------------------------
    def assign_leader(self, trainer: Trainer) -> None:
        """Assign the gym leader."""

        if self.leader is not None and self.leader.name != trainer.name:
            raise ValueError("Leader already assigned")
        self._validate_team(trainer.team)
        trainer.title = trainer.title or "Gym Leader"
        self.leader = trainer

    def add_trainer(self, trainer: Trainer) -> None:
        """Register an additional trainer for the gym."""

        self._validate_team(trainer.team)
        self.trainers.append(trainer)

    def assign_pokemon_to_trainer(self, trainer_name: str, pokemon: Pokemon) -> None:
        """Add a Pokemon to an existing trainer while enforcing restrictions."""

        target = self._find_trainer(trainer_name)
        if target is None:
            raise ValueError(f"Trainer '{trainer_name}' is not registered in the gym")
        self._ensure_pokemon_allowed(pokemon)
        additional_off_type = 0 if self.is_specialist(pokemon) else 1
        self._check_off_type_quota(additional_off_type)
        target.team.append(pokemon)

    def _find_trainer(self, trainer_name: str) -> Optional[Trainer]:
        lower = trainer_name.lower()
        for trainer in self._all_trainers:
            if trainer.name.lower() == lower:
                return trainer
        return None

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def summary(self) -> str:
        """Return a multi-line summary of the gym setup."""

        parts = [
            f"Gym: {self.name}",
            f"Specialty Type: {self.specialty_type}",
            f"Signature Move: {self.signature_move.title()}",
        ]

        if self.leader is not None:
            parts.append(f"Leader - {self.leader.describe()}")
        else:
            parts.append("Leader - Unassigned")

        if self.trainers:
            parts.append("Trainers:")
            parts.extend(f"  - {trainer.describe()}" for trainer in self.trainers)
        else:
            parts.append("Trainers: None yet")

        if self.rooms:
            parts.append("Rooms:")
            parts.extend(f"  - {room.describe()}" for room in self.rooms.values())
        else:
            parts.append("Rooms: None built")

        parts.append(
            f"Off-type Pokemon: {self.off_type_count}/{self.max_off_type}"
        )

        return "\n".join(parts)


class GymBuilder:
    """Convenience helper that guides the creation of a gym."""

    def __init__(
        self,
        name: str,
        specialty_type: str,
        signature_move: str,
        *,
        max_off_type: int = 2,
    ) -> None:
        self._gym = Gym(
            name,
            specialty_type,
            signature_move,
            max_off_type=max_off_type,
        )

    @property
    def gym(self) -> Gym:
        """Expose the underlying :class:`Gym` instance."""

        return self._gym

    # High level wrappers -------------------------------------------------
    def add_room(
        self,
        room_name: str,
        *,
        purpose: str,
        decorations: Optional[Sequence[str]] = None,
    ) -> "GymBuilder":
        self._gym.build_room(room_name, purpose=purpose, decorations=decorations)
        return self

    def set_leader(self, trainer: Trainer) -> "GymBuilder":
        self._gym.assign_leader(trainer)
        return self

    def add_trainer(self, trainer: Trainer) -> "GymBuilder":
        self._gym.add_trainer(trainer)
        return self

    def add_pokemon_to_trainer(self, trainer_name: str, pokemon: Pokemon) -> "GymBuilder":
        self._gym.assign_pokemon_to_trainer(trainer_name, pokemon)
        return self

    def build(self) -> Gym:
        """Return the configured gym."""

        return self._gym
