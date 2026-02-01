"""Fuzzy Inference System for CTF AI decision making."""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from config import GRID_COLS, GRID_ROWS, Team
from game_state import GameState, Move, Player, Point, generate_moves, manhattan_distance


# ========================== FUZZY MEMBERSHIP FUNCTIONS ====================


def fuzzy_distance_close(distance: float, max_dist: float = 20.0) -> float:
    """Membership function for 'close' distance (1.0 at 0, 0.0 at max_dist)."""
    if distance <= 0:
        return 1.0
    if distance >= max_dist:
        return 0.0
    return 1.0 - (distance / max_dist)


def fuzzy_distance_medium(distance: float, max_dist: float = 20.0) -> float:
    """Membership function for 'medium' distance (peak at max_dist/2)."""
    mid = max_dist / 2
    if distance <= 0:
        return 0.0
    if distance >= max_dist:
        return 0.0
    if distance <= mid:
        return distance / mid
    else:
        return 1.0 - ((distance - mid) / mid)


def fuzzy_distance_far(distance: float, max_dist: float = 20.0) -> float:
    """Membership function for 'far' distance (0.0 at 0, 1.0 at max_dist)."""
    if distance <= 0:
        return 0.0
    if distance >= max_dist:
        return 1.0
    return distance / max_dist


def fuzzy_threat_low(enemy_count: int, max_enemies: int = 5) -> float:
    """Membership function for 'low' threat."""
    if enemy_count <= 0:
        return 1.0
    if enemy_count >= max_enemies:
        return 0.0
    return 1.0 - (enemy_count / max_enemies)


def fuzzy_threat_high(enemy_count: int, max_enemies: int = 5) -> float:
    """Membership function for 'high' threat."""
    if enemy_count <= 0:
        return 0.0
    if enemy_count >= max_enemies:
        return 1.0
    return enemy_count / max_enemies


def fuzzy_player_ratio_weak(ratio: float) -> float:
    """Membership function for 'weak' player ratio (fewer players than opponent)."""
    if ratio >= 1.0:
        return 0.0
    return 1.0 - ratio


def fuzzy_player_ratio_strong(ratio: float) -> float:
    """Membership function for 'strong' player ratio (more players than opponent)."""
    if ratio <= 1.0:
        return 0.0
    return min(1.0, ratio - 1.0)


# ========================== FUZZY INFERENCE ENGINE ========================


class FuzzyInferenceAgent:
    """AI agent using Fuzzy Inference System for decision making."""

    def __init__(self, team: Team):
        self.team = team

    def select_move(self, state: GameState) -> Move:
        """Select move using fuzzy logic."""
        legal_moves = generate_moves(state)
        if not legal_moves:
            # Fallback
            active = state.active_players(self.team)
            if active:
                return Move(self.team, active[0].player_id, "STAY")
            raise RuntimeError("No legal moves")

        # Score each move using fuzzy rules
        move_scores: List[Tuple[Move, float]] = []
        for move in legal_moves:
            score = self._evaluate_move_fuzzy(state, move)
            move_scores.append((move, score))

        # Select highest scoring move
        best_move = max(move_scores, key=lambda x: x[1])[0]
        return best_move

    def _evaluate_move_fuzzy(self, state: GameState, move: Move) -> float:
        """Evaluate a move using fuzzy inference rules."""
        player = state.get_player(move.team, move.player_id)
        
        # Simulate move to get new position
        from game_state import DIRECTION_DELTA
        dr, dc = DIRECTION_DELTA[move.action]
        new_pos = player.position.translate(dr, dc)
        
        if not new_pos.in_bounds():
            return 0.0

        # Calculate fuzzy inputs
        opponent = state.opponent(self.team)
        opponent_hoop = state.layout.hula_hoops[opponent]
        own_safe_zone = state.layout.safe_zones[self.team]
        
        # Input 1: Distance to opponent flag
        dist_to_flag = manhattan_distance(new_pos, opponent_hoop)
        flag_close = fuzzy_distance_close(dist_to_flag, max_dist=15)
        flag_medium = fuzzy_distance_medium(dist_to_flag, max_dist=15)
        flag_far = fuzzy_distance_far(dist_to_flag, max_dist=15)

        # Input 2: Distance to own safe zone (for scoring/safety)
        own_safe_center = Point(
            row=(own_safe_zone.top + own_safe_zone.bottom) // 2,
            col=(own_safe_zone.left + own_safe_zone.right) // 2,
        )
        dist_to_safe = manhattan_distance(new_pos, own_safe_center)
        safe_close = fuzzy_distance_close(dist_to_safe, max_dist=10)
        safe_far = fuzzy_distance_far(dist_to_safe, max_dist=10)

        # Input 3: Nearby enemy threat
        nearby_enemies = sum(
            1 for p in state.active_players(opponent)
            if manhattan_distance(p.position, new_pos) <= 3
        )
        threat_low = fuzzy_threat_low(nearby_enemies, max_enemies=4)
        threat_high = fuzzy_threat_high(nearby_enemies, max_enemies=4)

        # Input 4: Player ratio (strength)
        active_self = len(state.active_players(self.team))
        active_opp = len(state.active_players(opponent))
        ratio = active_self / max(1, active_opp)
        weak = fuzzy_player_ratio_weak(ratio)
        strong = fuzzy_player_ratio_strong(ratio)

        # Input 5: Carrying pin status
        carrying = 1.0 if player.carrying_pin else 0.0

        # FUZZY RULES (IF-THEN rules with weights)
        score = 0.0

        # Rule 1: If carrying pin AND close to safe zone → HIGH priority (score + return)
        rule1_activation = min(carrying, safe_close)
        score += rule1_activation * 100.0

        # Rule 2: If NOT carrying AND close to opponent flag AND threat is low → attack
        rule2_activation = min((1.0 - carrying), flag_close, threat_low)
        score += rule2_activation * 80.0

        # Rule 3: If NOT carrying AND flag is medium distance AND strong → advance
        rule3_activation = min((1.0 - carrying), flag_medium, strong)
        score += rule3_activation * 50.0

        # Rule 4: If high threat AND weak → retreat to safe zone
        rule4_activation = min(threat_high, weak, safe_far)
        score += rule4_activation * 70.0

        # Rule 5: If carrying pin AND high threat → defensive escape
        rule5_activation = min(carrying, threat_high)
        score += rule5_activation * 90.0

        # Rule 6: If close to opponent flag AND can pickup → go for it
        can_pickup = (
            state.carrier_count(self.team) < 1
            and state.pins_at_hoop[opponent] > 0
        )
        if can_pickup:
            rule6_activation = flag_close
            score += rule6_activation * 95.0

        # Rule 7: If at opponent jail AND teammates jailed → rescue
        opponent_jail = state.layout.jail_cells[opponent]
        dist_to_jail = manhattan_distance(new_pos, opponent_jail)
        jailed_count = len(state.jailed_players(self.team))
        if jailed_count > 0:
            jail_close = fuzzy_distance_close(dist_to_jail, max_dist=12)
            rule7_activation = jail_close
            score += rule7_activation * 85.0

        # Rule 8: General positioning - prefer center columns
        center_col = GRID_COLS // 2
        col_distance = abs(new_pos.col - center_col)
        center_preference = 1.0 - (col_distance / (GRID_COLS / 2))
        score += center_preference * 10.0

        # Penalty for STAY (encourage movement)
        if move.action == "STAY":
            score *= 0.5

        return score


# ========================== FACTORY FUNCTION ==============================


def create_fuzzy_agent(team: Team) -> FuzzyInferenceAgent:
    """Create a Fuzzy Inference System agent."""
    return FuzzyInferenceAgent(team)
