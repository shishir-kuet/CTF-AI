"""Main game loop and simulation for CTF AI vs AI."""

from __future__ import annotations

import argparse
import time
from typing import Optional

from ai import AIAgent, get_ai_agent
from config import GRID_COLS, GRID_ROWS, Team
from game_state import GameState, apply_move, create_initial_state

try:
    from pygame_view import PygameRenderer
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


# ========================== PYGAME SIMULATION =============================


def run_pygame_simulation(
    agent_a: AIAgent,
    agent_b: AIAgent,
    delay: float = 1.0,
    max_turns: Optional[int] = None,
) -> GameState:
    """
    Run AI vs AI game with Pygame visual rendering.
    
    Args:
        agent_a: AI controlling Team A
        agent_b: AI controlling Team B
        delay: Seconds to pause between moves
        max_turns: Stop after N turns (None = play until terminal)
    
    Returns:
        Final game state
    """
    if not PYGAME_AVAILABLE:
        print("ERROR: Pygame not available. Install with: pip install pygame")
        raise ImportError("pygame required for visual mode")
    
    renderer = PygameRenderer()
    state = create_initial_state()
    agents = {Team.A: agent_a, Team.B: agent_b}
    
    last_move_str = None
    
    # Initial render
    renderer.render(state, last_move_str)
    renderer.wait(1000)  # Wait 1 second at start
    
    try:
        while renderer.running and not state.is_terminal():
            # Check for quit
            if not renderer.handle_events():
                break
            
            # Check max turns
            if max_turns and state.turn_count >= max_turns:
                print(f"\nStopped at turn {max_turns}")
                break
            
            # AI selects move
            current_agent = agents[state.current_turn]
            move = current_agent.select_move(state)
            last_move_str = str(move)
            
            # Apply move
            state = apply_move(state, move)
            
            # Render updated state
            renderer.render(state, last_move_str)
            
            # Delay
            if delay > 0:
                renderer.wait(int(delay * 1000))
        
        # Show final state
        if state.is_terminal():
            renderer.render(state, "GAME OVER")
            winner = state.winner()
            print("\n" + "="*60)
            print("GAME OVER")
            print("="*60)
            if winner:
                print(f"Winner: Team {winner.value}")
            else:
                print("Draw")
            print(f"Total turns: {state.turn_count}")
            print(f"Score A: {state.pins_captured[Team.A]}, B: {state.pins_captured[Team.B]}")
            
            # Keep window open
            print("\nClose window or press ESC to exit...")
            while renderer.running:
                if not renderer.handle_events():
                    break
                renderer.wait(100)
    
    finally:
        renderer.close()
    
    return state


# ========================== HEADLESS SIMULATION ===========================


def print_game_state(state: GameState, compact: bool = True):
    """Print the current game state to console."""
    if compact:
        print(f"\n{'='*60}")
        print(f"Turn {state.turn_count} | Current: Team {state.current_turn.value}")
        print(f"{'='*60}")
        
        for team in [Team.A, Team.B]:
            active = len(state.active_players(team))
            jailed = len(state.jailed_players(team))
            pins_remaining = state.pins_at_hoop[team]
            pins_scored = state.pins_captured[team]
            carriers = state.carrier_count(team)
            
            print(f"Team {team.value}: Active={active}, Jailed={jailed}, "
                  f"Pins@Hoop={pins_remaining}, Captured={pins_scored}, Carriers={carriers}")
    else:
        # Full grid visualization
        print(f"\nTurn {state.turn_count} | Team {state.current_turn.value}'s turn")
        print_grid(state)
        print(f"\nTeam A: Pins captured={state.pins_captured[Team.A]}, "
              f"@Hoop={state.pins_at_hoop[Team.A]}")
        print(f"Team B: Pins captured={state.pins_captured[Team.B]}, "
              f"@Hoop={state.pins_at_hoop[Team.B]}")


def print_grid(state: GameState):
    """Print ASCII representation of the game grid."""
    # Build grid
    grid = [["." for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    
    # Mark safe zones
    for team, rect in state.layout.safe_zones.items():
        for cell in rect.cells():
            if cell.in_bounds():
                grid[cell.row][cell.col] = "S" if team is Team.A else "s"
    
    # Mark hula hoops
    for team, pos in state.layout.hula_hoops.items():
        grid[pos.row][pos.col] = "H" if team is Team.A else "h"
    
    # Mark jails
    for team, pos in state.layout.jail_cells.items():
        grid[pos.row][pos.col] = "J" if team is Team.A else "j"
    
    # Mark players
    for player in state.players:
        if not player.jailed:
            pos = player.position
            if player.carrying_pin:
                symbol = "A" if player.team is Team.A else "B"  # Uppercase = carrier
            else:
                symbol = "a" if player.team is Team.A else "b"  # Lowercase = normal
            
            # Overwrite with player (players are more important to see)
            if grid[pos.row][pos.col] in [".", "S", "s"]:
                grid[pos.row][pos.col] = symbol
            else:
                # Multiple on same cell, show with @
                grid[pos.row][pos.col] = "@"
    
    # Print grid with row numbers
    print("  " + "".join(str(i % 10) for i in range(GRID_COLS)))
    for r, row in enumerate(grid):
        print(f"{r} {''.join(row)}")
    
    print("\nLegend: A/a=Team A player, B/b=Team B player (uppercase=carrying pin)")
    print("        H/h=Hula hoop, J/j=Jail, S/s=Safe zone, @=multiple units")


def run_headless_simulation(
    agent_a: AIAgent,
    agent_b: AIAgent,
    verbose: bool = True,
    delay: float = 0.0,
    print_every: int = 10,
) -> GameState:
    """
    Run a complete AI vs AI game without graphics.
    
    Args:
        agent_a: AI controlling Team A
        agent_b: AI controlling Team B
        verbose: Print state updates
        delay: Seconds to pause between moves (for viewing)
        print_every: Print state every N turns (if verbose)
    
    Returns:
        Final game state
    """
    state = create_initial_state()
    
    if verbose:
        print("\n" + "="*60)
        print("STARTING CTF AI vs AI SIMULATION")
        print("="*60)
        print(f"Agent A: {agent_a.__class__.__name__}")
        print(f"Agent B: {agent_b.__class__.__name__}")
        print_game_state(state, compact=False)
    
    agents = {Team.A: agent_a, Team.B: agent_b}
    
    while not state.is_terminal():
        current_agent = agents[state.current_turn]
        
        # AI selects move
        move = current_agent.select_move(state)
        
        if verbose and (state.turn_count % print_every == 0 or state.turn_count < 5):
            print(f"\nTurn {state.turn_count}: Team {state.current_turn.value} → {move}")
        
        # Apply move
        state = apply_move(state, move)
        
        if verbose and (state.turn_count % print_every == 0):
            print_game_state(state, compact=True)
        
        if delay > 0:
            time.sleep(delay)
    
    # Game over
    if verbose:
        print("\n" + "="*60)
        print("GAME OVER")
        print("="*60)
        print_game_state(state, compact=False)
        winner = state.winner()
        if winner:
            print(f"\n🏆 Winner: Team {winner.value}")
        else:
            print("\n🤝 Game ended in a draw")
        print(f"Total turns: {state.turn_count}")
    
    return state


# ========================== MAIN ENTRY POINT ==============================


def main():
    parser = argparse.ArgumentParser(
        description="Capture the Flag AI vs AI simulation"
    )
    parser.add_argument(
        "--agent-a",
        type=str,
        default="minimax",
        choices=["minimax", "random", "fuzzy"],
        help="AI type for Team A (default: minimax)",
    )
    parser.add_argument(
        "--agent-b",
        type=str,
        default="fuzzy",
        choices=["minimax", "random", "fuzzy"],
        help="AI type for Team B (default: fuzzy)",
    )
    parser.add_argument(
        "--depth-a",
        type=int,
        default=3,
        help="Minimax depth for Team A (default: 3)",
    )
    parser.add_argument(
        "--depth-b",
        type=int,
        default=3,
        help="Minimax depth for Team B (default: 3)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay in seconds between moves (default: 0.0)",
    )
    parser.add_argument(
        "--print-every",
        type=int,
        default=10,
        help="Print state every N turns (default: 10)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress most output (only show final result)",
    )
    parser.add_argument(
        "--pygame",
        action="store_true",
        help="Use Pygame visualization (graphical window)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Stop simulation after N turns (default: run until terminal)",
    )
    
    args = parser.parse_args()
    
    # Create agents
    agent_a = get_ai_agent(Team.A, args.agent_a, args.depth_a)
    agent_b = get_ai_agent(Team.B, args.agent_b, args.depth_b)
    
    # Choose rendering mode
    if args.pygame:
        if not PYGAME_AVAILABLE:
            print("ERROR: Pygame not installed. Install with: pip install pygame")
            print("Falling back to terminal mode...")
            final_state = run_headless_simulation(
                agent_a=agent_a,
                agent_b=agent_b,
                verbose=not args.quiet,
                delay=args.delay,
                print_every=args.print_every,
            )
        else:
            final_state = run_pygame_simulation(
                agent_a=agent_a,
                agent_b=agent_b,
                delay=args.delay,
                max_turns=args.max_turns,
            )
    else:
        # Headless terminal mode
        final_state = run_headless_simulation(
            agent_a=agent_a,
            agent_b=agent_b,
            verbose=not args.quiet,
            delay=args.delay,
            print_every=args.print_every,
        )
    
    # Summary
    if args.quiet:
        winner = final_state.winner()
        if winner:
            print(f"Winner: Team {winner.value}")
        else:
            print("Draw")
        print(f"Turns: {final_state.turn_count}")
        print(f"Score A: {final_state.pins_captured[Team.A]}, B: {final_state.pins_captured[Team.B]}")


if __name__ == "__main__":
    main()
