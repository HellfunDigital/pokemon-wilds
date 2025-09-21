import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from gym_builder import GymBuilder, Pokemon, Trainer


def make_fire_gym(max_off_type=2):
    return GymBuilder(
        "Blazing Beacon",
        specialty_type="Fire",
        signature_move="flame burst",
        max_off_type=max_off_type,
    )


def make_pokemon(name, types, moves=()):
    return Pokemon(name=name, types=set(types), moves=set(moves))


def test_can_construct_gym_with_rooms_and_leader():
    builder = make_fire_gym()
    charizard = make_pokemon("Charizard", {"Fire", "Flying"}, {"Flame Burst"})
    arcanine = make_pokemon("Arcanine", {"Fire"}, {"Flame Burst"})
    leader = Trainer("Flannery", team=[charizard, arcanine])

    builder.set_leader(leader)
    builder.add_room("Entrance", purpose="Welcome challengers", decorations=["Torches"])
    builder.add_room("Battlefield", purpose="Final showdown")

    gym = builder.build()

    summary = gym.summary()
    assert "Gym: Blazing Beacon" in summary
    assert "Leader - Flannery (Gym Leader): Charizard, Arcanine" in summary
    assert "Rooms:" in summary
    assert "Battlefield" in summary


def test_off_type_pokemon_requires_signature_move():
    builder = make_fire_gym()
    lapras = make_pokemon("Lapras", {"Water", "Ice"})
    trainer = Trainer("Kai", team=[lapras])

    with pytest.raises(ValueError):
        builder.add_trainer(trainer)

    lapras.learn_move("Flame Burst")
    builder.add_trainer(trainer)
    assert "Lapras" in builder.gym.summary()


def test_enforces_global_off_type_limit():
    builder = make_fire_gym(max_off_type=2)

    lapras = make_pokemon("Lapras", {"Water", "Ice"}, {"Flame Burst"})
    tyranitar = make_pokemon("Tyranitar", {"Rock", "Dark"}, {"Flame Burst"})
    empoleon = make_pokemon("Empoleon", {"Water", "Steel"}, {"Flame Burst"})

    leader = Trainer("Flannery", team=[make_pokemon("Torkoal", {"Fire"}, {"Flame Burst"})])
    builder.set_leader(leader)

    builder.add_trainer(Trainer("Kai", team=[lapras]))
    builder.add_trainer(Trainer("Cynthia", team=[tyranitar]))

    with pytest.raises(ValueError):
        builder.add_trainer(Trainer("Wallace", team=[empoleon]))


def test_assign_pokemon_to_existing_trainer_respects_rules():
    builder = make_fire_gym()

    leader = Trainer("Flannery", team=[make_pokemon("Torkoal", {"Fire"}, {"Flame Burst"})])
    builder.set_leader(leader)
    builder.add_trainer(Trainer("Kai", team=[]))

    builder.add_pokemon_to_trainer(
        "Kai", make_pokemon("Ninetales", {"Fire"}, {"Flame Burst"})
    )

    with pytest.raises(ValueError):
        builder.add_pokemon_to_trainer(
            "Kai", make_pokemon("Gyarados", {"Water", "Flying"})
        )

    builder.add_pokemon_to_trainer(
        "Kai", make_pokemon("Gyarados", {"Water", "Flying"}, {"Flame Burst"})
    )

    assert "Gyarados" in builder.gym.summary()
