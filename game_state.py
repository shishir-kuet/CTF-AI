"""Game state representation, move generation, and state transitions for CTF."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from config import (
    DEFAULT_LAYOUT,
    GRID_COLS,
    GRID_ROWS,
    HEURISTIC_DISTANCE_WEIGHT,
    HEURISTIC_PIN_SCORE,
    HEURISTIC_PLAYER_SCORE,
    MAX_PIN_CARRIERS_PER_TEAM,
    MAX_TURNS,
    MIDLINE_ROW,
    PINS_PER_TEAM,
    TEAM_SIZE,
    Layout,
    Point,
    Team,
)


# ========================== PLAYER STATE ==================================


@dataclass(frozen=True)
class Player:
    """Represents a single player (agent) on the field."""

    team: Team
    player_id: int  # 0..9 within team
    position: Point
    jailed: bool = False
    carrying_pin: bool = False
    rescue_immunity: bool = False  # True after being rescued until crossing midline

    def __post_init__(self):
        assert 0 <= self.player_id < TEAM_SIZE

    @property
    def is_active(self) -> bool:
        """Can this player move or be selected?"""
        return not self.jailed


# ========================== GAME STATE ====================================


@dataclass(frozen=True)
class GameState:
    """Immutable snapshot of the entire game."""

    layout: Layout
    players: Tuple[Player, ...]  # All 20 players (10 per team)
    pins_at_hoop: Dict[Team, int]  # How many pins remain at each hoop
    pins_captured: Dict[Team, int]  # Score: how many pins each team deposited
    current_turn: Team
    turn_count: int = 0

    def __post_init__(self):
        # Validate structure
        assert len(self.players) == 2 * TEAM_SIZE
        team_a_count = sum(1 for p in self.players if p.team is Team.A)
        team_b_count = sum(1 for p in self.players if p.team is Team.B)
        assert team_a_count == TEAM_SIZE and team_b_count == TEAM_SIZE

    # ------------------ Accessors -----------------------------------------

    def get_player(self, team: Team, player_id: int) -> Player:
        """Retrieve a specific player by team and id."""
        for p in self.players:
            if p.team is team and p.player_id == player_id:
                return p
        raise ValueError(f"Player {team.value}:{player_id} not found")

    def team_players(self, team: Team) -> List[Player]:
        """All players (active or jailed) for a given team."""
        return [p for p in self.players if p.team is team]

    def active_players(self, team: Team) -> List[Player]:
        """Free (non-jailed) players for a given team."""
        return [p for p in self.players if p.team is team and p.is_active]

    def jailed_players(self, team: Team) -> List[Player]:
        """Jailed players for a given team."""
        return [p for p in self.players if p.team is team and p.jailed]

    def carrier_count(self, team: Team) -> int:
        """How many players on this team are currently carrying a pin."""
        return sum(1 for p in self.team_players(team) if p.carrying_pin)

    def opponent(self, team: Team) -> Team:
        return Team.B if team is Team.A else Team.A

    # ------------------ Zone checks ---------------------------------------

    def in_safe_zone(self, point: Point) -> bool:
        """Is this point inside any safe zone (either team)?"""
        return any(rect.contains(point) for rect in self.layout.safe_zones.values())

    def in_own_safe_zone(self, player: Player) -> bool:
        """Is the player inside their own safe zone?"""
        return self.layout.safe_zones[player.team].contains(player.position)

    def at_opponent_hoop(self, player: Player) -> bool:
        """Is the player at the opponent's hula hoop cell?"""
        opp = self.opponent(player.team)
        return player.position == self.layout.hula_hoops[opp]

    def at_own_hoop(self, player: Player) -> bool:
        """Is the player at their own hula hoop cell?"""
        return player.position == self.layout.hula_hoops[player.team]

    def at_opponent_jail(self, player: Player) -> bool:
        """Is the player at their own team's jail cell where teammates are held?
        Note: jail_cells[Team.A] is where Team A players are jailed (in opponent territory).
        """
        return player.position == self.layout.jail_cells[player.team]

    def crossed_to_own_territory(self, player: Player) -> bool:
        """Did the player cross back to their own side (row-based check)?"""
        if player.team is Team.A:
            return player.position.row <= MIDLINE_ROW
        return player.position.row > MIDLINE_ROW

    def in_opponent_territory(self, player: Player) -> bool:
        """Is the player in opponent's territory?"""
        if player.team is Team.A:
            # Team A is in opponent territory if row > MIDLINE_ROW (in Team B's side)
            return player.position.row > MIDLINE_ROW
        else:
            # Team B is in opponent territory if row <= MIDLINE_ROW (in Team A's side)
            return player.position.row <= MIDLINE_ROW

    # ------------------ Terminal / Win Checks -----------------------------

    def is_terminal(self) -> bool:
        """Check if the game has ended."""
        # Win condition 1: a team collected all 6 pins at their hoop
        if any(count >= 6 for count in self.pins_at_hoop.values()):
            return True
        # Win condition 2: a team has all 10 players jailed
        if len(self.jailed_players(Team.A)) >= TEAM_SIZE:
            return True
        if len(self.jailed_players(Team.B)) >= TEAM_SIZE:
            return True
        # Win condition 3: a team has no active players (all jailed)
        if len(self.active_players(Team.A)) == 0:
            return True
        if len(self.active_players(Team.B)) == 0:
            return True
        # Max turn limit
        if self.turn_count >= MAX_TURNS:
            return True
        return False

    def winner(self) -> Optional[Team]:
        """Return the winning team, or None if draw/ongoing."""
        if not self.is_terminal():
            return None

        # Primary: pins at hoop (team with 6 pins wins)
        if self.pins_at_hoop[Team.A] >= 6:
            return Team.A
        if self.pins_at_hoop[Team.B] >= 6:
            return Team.B

        # Secondary: check if all players jailed
        if len(self.active_players(Team.A)) == 0:
            return Team.B
        if len(self.active_players(Team.B)) == 0:
            return Team.A

        # Tie-breaker: more pins at hoop
        if self.pins_at_hoop[Team.A] > self.pins_at_hoop[Team.B]:
            return Team.A
        if self.pins_at_hoop[Team.B] > self.pins_at_hoop[Team.A]:
            return Team.B

        # Final tie-breaker: more free players
        active_a = len(self.active_players(Team.A))
        active_b = len(self.active_players(Team.B))
        if active_a > active_b:
            return Team.A
        if active_b > active_a:
            return Team.B

        return None  # Draw

    # ------------------ Utility / Evaluation ------------------------------

    def utility(self, team: Team) -> float:
        """
        Heuristic evaluation from the perspective of `team`.
        Matches the agreed evaluation function:
          +100 × (pins_captured_by_self)
          -100 × (pins_captured_by_opponent)
          +10 × (free_players_self - free_players_opponent)
          - distance_to_opponent_pins
          + distance_of_opponent_to_self_pins
        """
        opp = self.opponent(team)

        # Pin score difference
        pin_diff = self.pins_captured[team] - self.pins_captured[opp]
        score = HEURISTIC_PIN_SCORE * pin_diff

        # Free player difference
        active_self = len(self.active_players(team))
        active_opp = len(self.active_players(opp))
        player_diff = active_self - active_opp
        score += HEURISTIC_PLAYER_SCORE * player_diff

        # Distance to opponent pins (lower is better for attack)
        opp_hoop = self.layout.hula_hoops[opp]
        for p in self.active_players(team):
            dist = manhattan_distance(p.position, opp_hoop)
            score -= HEURISTIC_DISTANCE_WEIGHT * dist

        # Distance of opponent to our pins (higher is better for defense)
        self_hoop = self.layout.hula_hoops[team]
        for p in self.active_players(opp):
            dist = manhattan_distance(p.position, self_hoop)
            score += HEURISTIC_DISTANCE_WEIGHT * dist

        return score


# ========================== MOVE REPRESENTATION ===========================


@dataclass(frozen=True)
class Move:
    """A single action: select one player and do one thing."""

    team: Team
    player_id: int
    action: str  # "STAY", "UP", "DOWN", "LEFT", "RIGHT"

    def __str__(self) -> str:
        return f"{self.team.value}{self.player_id}:{self.action}"


# Movement deltas
DIRECTION_DELTA = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1),
    "STAY": (0, 0),
}


# ========================== MOVE GENERATION ===============================


def generate_moves(state: GameState) -> List[Move]:
    """Generate all legal moves for the current team's turn."""
    team = state.current_turn
    moves: List[Move] = []

    for player in state.active_players(team):
        # STAY is always legal
        moves.append(Move(team, player.player_id, "STAY"))

        # Try each direction
        for direction in ["UP", "DOWN", "LEFT", "RIGHT"]:
            dr, dc = DIRECTION_DELTA[direction]
            new_pos = player.position.translate(dr, dc)
            if new_pos.in_bounds():
                moves.append(Move(team, player.player_id, direction))

    return moves


# ========================== STATE TRANSITION ==============================


def apply_move(state: GameState, move: Move) -> GameState:
    """
    Apply a move and return a new immutable GameState.
    Handles all rule logic: movement, capture, pin pickup, deposit, rescue, immunity.
    """
    assert move.team is state.current_turn

    player = state.get_player(move.team, move.player_id)
    if not player.is_active:
        # Cannot move jailed player (should never happen in legal moves)
        return _next_turn(state)

    # Compute new position
    dr, dc = DIRECTION_DELTA[move.action]
    new_pos = player.position.translate(dr, dc)
    if not new_pos.in_bounds():
        # Out of bounds → no-op, just pass turn
        return _next_turn(state)

    # Create mutable working copy
    new_players = list(state.players)
    pins_at_hoop = dict(state.pins_at_hoop)
    pins_captured = dict(state.pins_captured)

    # Update player position
    idx = _find_player_index(new_players, player.team, player.player_id)
    new_players[idx] = replace(new_players[idx], position=new_pos)
    moved_player = new_players[idx]

    # Check immunity expiration: if player crossed back to own territory
    if moved_player.rescue_immunity and state.crossed_to_own_territory(moved_player):
        new_players[idx] = replace(new_players[idx], rescue_immunity=False)
        moved_player = new_players[idx]

    # ---- SAFE ZONE CHECK ----
    in_safe = state.in_safe_zone(new_pos)

    # ---- CAPTURE LOGIC ----
    # Capture can happen when:
    # 1. Moving player is in opponent territory (invasion)
    # 2. Opponent is in their own territory but collides with invader
    # 3. Both players not in safe zones and no immunity
    if not in_safe and not moved_player.rescue_immunity:
        opp_team = state.opponent(move.team)
        for i, p in enumerate(new_players):
            if (
                p.team is opp_team
                and p.position == new_pos
                and p.is_active
                and not state.in_safe_zone(p.position)
                and not p.rescue_immunity
            ):
                # Determine who captures whom based on territory
                # If moved_player is in opponent territory, they can be captured
                if state.in_opponent_territory(moved_player):
                    # Moving player is invading - they get captured!
                    new_players[idx] = replace(moved_player, jailed=True, carrying_pin=False)
                    if moved_player.carrying_pin:
                        pins_at_hoop[move.team] += 1
                    moved_player = new_players[idx]
                # If the stationary player is in opponent territory, they get captured
                elif state.in_opponent_territory(p):
                    # Stationary opponent is invading - they get captured!
                    new_players[i] = replace(p, jailed=True, carrying_pin=False)
                    if p.carrying_pin:
                        pins_at_hoop[opp_team] += 1
                break

    # ---- PIN CAPTURE (at opponent hoop, transfer to own hoop) ----
    if state.at_opponent_hoop(moved_player):
        opp_team = state.opponent(move.team)
        # Transfer pin: opponent loses 1, own team gains 1 at hoop
        if pins_at_hoop[opp_team] > 0:
            pins_at_hoop[opp_team] -= 1  # Opponent loses pin from their hoop
            pins_at_hoop[move.team] += 1  # Own team gains pin at their hoop
            pins_captured[move.team] += 1  # Track score for statistics
            # Teleport player back to their release point (safe return)
            release_point = state.layout.release_points[move.team]
            new_players[idx] = replace(new_players[idx], position=release_point)
            moved_player = new_players[idx]

    # ---- JAIL RESCUE ----
    if state.at_opponent_jail(moved_player):
        opp_team = state.opponent(move.team)
        # Find jailed teammates
        jailed = [
            i for i, p in enumerate(new_players) if p.team is move.team and p.jailed
        ]
        if jailed:
            # Free one jailed teammate
            freed_idx = jailed[0]
            release_point = state.layout.release_points[move.team]
            new_players[freed_idx] = replace(
                new_players[freed_idx],
                jailed=False,
                position=release_point,
                rescue_immunity=True,
            )
            # Rescuer also teleports with immunity
            new_players[idx] = replace(
                new_players[idx], position=release_point, rescue_immunity=True
            )

    # Advance turn
    next_team = state.opponent(state.current_turn)
    return GameState(
        layout=state.layout,
        players=tuple(new_players),
        pins_at_hoop=pins_at_hoop,
        pins_captured=pins_captured,
        current_turn=next_team,
        turn_count=state.turn_count + 1,
    )


# ========================== HELPERS =======================================


def _next_turn(state: GameState) -> GameState:
    """Advance turn without changing anything else."""
    return replace(
        state,
        current_turn=state.opponent(state.current_turn),
        turn_count=state.turn_count + 1,
    )


def _find_player_index(players: List[Player], team: Team, player_id: int) -> int:
    for i, p in enumerate(players):
        if p.team is team and p.player_id == player_id:
            return i
    raise ValueError(f"Player {team.value}:{player_id} not found")


def manhattan_distance(a: Point, b: Point) -> int:
    return abs(a.row - b.row) + abs(a.col - b.col)


# ========================== INITIAL STATE =================================


def create_initial_state(layout: Layout = DEFAULT_LAYOUT) -> GameState:
    """Build the starting game state with 10 players per team auto-placed."""
    players: List[Player] = []

    # Team A: place 10 players near their safe zone / hoop area (top)
    team_a_spawn_rows = [0, 1, 2]
    team_a_spawn_cols = list(range(GRID_COLS))
    spawn_points_a = [
        Point(r, c) for r in team_a_spawn_rows for c in team_a_spawn_cols
    ]
    for pid in range(TEAM_SIZE):
        pos = spawn_points_a[pid % len(spawn_points_a)]
        players.append(Player(team=Team.A, player_id=pid, position=pos))

    # Team B: place 10 players near their safe zone / hoop area (bottom)
    team_b_spawn_rows = [GRID_ROWS - 3, GRID_ROWS - 2, GRID_ROWS - 1]
    team_b_spawn_cols = list(range(GRID_COLS))
    spawn_points_b = [
        Point(r, c) for r in team_b_spawn_rows for c in team_b_spawn_cols
    ]
    for pid in range(TEAM_SIZE):
        pos = spawn_points_b[pid % len(spawn_points_b)]
        players.append(Player(team=Team.B, player_id=pid, position=pos))

    return GameState(
        layout=layout,
        players=tuple(players),
        pins_at_hoop={Team.A: PINS_PER_TEAM, Team.B: PINS_PER_TEAM},
        pins_captured={Team.A: 0, Team.B: 0},
        current_turn=Team.A,
        turn_count=0,
    )
