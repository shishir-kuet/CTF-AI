"""AI agents for the CTF game: Minimax with Alpha-Beta pruning."""

from __future__ import annotations

import math
from typing import Optional, Tuple

from config import MINIMAX_DEPTH_TEAM_A, Team
from game_state import GameState, Move, apply_move, generate_moves


# ========================== MINIMAX + ALPHA-BETA ==========================


def minimax_alpha_beta(
    state: GameState,
    depth: int,
    alpha: float,
    beta: float,
    maximizing_team: Team,
) -> Tuple[float, Optional[Move]]:
    """
    Minimax with Alpha-Beta pruning.
    
    Args:
        state: Current game state
        depth: Remaining search depth (plies)
        alpha: Best value for maximizer found so far
        beta: Best value for minimizer found so far
        maximizing_team: Which team we're evaluating utility for (Team A in our case)
    
    Returns:
        (utility_score, best_move)
        If depth=0 or terminal, best_move is None
    """
    # Base case: terminal state or depth limit reached
    if depth == 0 or state.is_terminal():
        return state.utility(maximizing_team), None

    # Generate all legal moves for the current player
    moves = generate_moves(state)
    
    # If no legal moves (shouldn't happen but defensively handled)
    if not moves:
        return state.utility(maximizing_team), None

    best_move: Optional[Move] = None
    
    # Determine if current turn is maximizing or minimizing
    is_maximizing = state.current_turn is maximizing_team

    if is_maximizing:
        # Maximizing player
        max_eval = -math.inf
        for move in moves:
            new_state = apply_move(state, move)
            eval_score, _ = minimax_alpha_beta(
                new_state, depth - 1, alpha, beta, maximizing_team
            )
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Beta cutoff
        return max_eval, best_move
    else:
        # Minimizing player
        min_eval = math.inf
        for move in moves:
            new_state = apply_move(state, move)
            eval_score, _ = minimax_alpha_beta(
                new_state, depth - 1, alpha, beta, maximizing_team
            )
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move
            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Alpha cutoff
        return min_eval, best_move


# ========================== AI AGENT INTERFACE ============================


class AIAgent:
    """Base class for AI agents."""
    
    def __init__(self, team: Team):
        self.team = team
    
    def select_move(self, state: GameState) -> Move:
        """Select and return a move for the current state."""
        raise NotImplementedError


class MinimaxAgent(AIAgent):
    """AI agent using Minimax with Alpha-Beta pruning."""
    
    def __init__(self, team: Team, depth: int = MINIMAX_DEPTH_TEAM_A):
        super().__init__(team)
        self.depth = depth
    
    def select_move(self, state: GameState) -> Move:
        """Select the best move using Minimax + Alpha-Beta."""
        assert state.current_turn is self.team, "Not this agent's turn"
        
        _, best_move = minimax_alpha_beta(
            state=state,
            depth=self.depth,
            alpha=-math.inf,
            beta=math.inf,
            maximizing_team=self.team,
        )
        
        # Fallback if no move found (shouldn't happen)
        if best_move is None:
            moves = generate_moves(state)
            if moves:
                best_move = moves[0]
            else:
                # Emergency: create a STAY move
                active = state.active_players(self.team)
                if active:
                    best_move = Move(self.team, active[0].player_id, "STAY")
                else:
                    raise RuntimeError("No active players and no legal moves")
        
        return best_move


class RandomAgent(AIAgent):
    """Baseline agent that picks random legal moves."""
    
    def select_move(self, state: GameState) -> Move:
        import random
        moves = generate_moves(state)
        if not moves:
            # Emergency fallback
            active = state.active_players(self.team)
            if active:
                return Move(self.team, active[0].player_id, "STAY")
            raise RuntimeError("No legal moves available")
        return random.choice(moves)


# ========================== CONVENIENCE FUNCTIONS =========================


def get_ai_agent(team: Team, agent_type: str = "minimax", depth: int = MINIMAX_DEPTH_TEAM_A) -> AIAgent:
    """
    Factory function to create AI agents.
    
    Args:
        team: Which team this agent controls
        agent_type: "minimax", "random", or "fuzzy"
        depth: Search depth for minimax (ignored for random/fuzzy)
    
    Returns:
        AIAgent instance
    """
    if agent_type.lower() == "minimax":
        return MinimaxAgent(team, depth)
    elif agent_type.lower() == "random":
        return RandomAgent(team)
    elif agent_type.lower() == "fuzzy":
        from fuzzy_ai import create_fuzzy_agent
        return create_fuzzy_agent(team)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
