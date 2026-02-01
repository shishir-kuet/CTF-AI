"""Pygame visual renderer for CTF game."""

from __future__ import annotations

import math
import pygame
from typing import Optional

from config import GRID_COLS, GRID_ROWS, Team
from game_state import GameState


# ========================== VISUAL CONSTANTS ==============================

# Window sizing
CELL_SIZE = 60  # INCREASED from 50 for better visibility
SIDEBAR_WIDTH = 350  # INCREASED for more info
WINDOW_WIDTH = GRID_COLS * CELL_SIZE + SIDEBAR_WIDTH
WINDOW_HEIGHT = GRID_ROWS * CELL_SIZE + 120  # +120 for top info bar

# Colors (RGB) - ENHANCED color palette
COLOR_BG = (20, 24, 32)  # Dark blue-gray background
COLOR_GRID = (50, 55, 65)
COLOR_TEAM_A_TERRITORY = (25, 40, 80)  # Deep blue
COLOR_TEAM_B_TERRITORY = (80, 30, 30)  # Deep red

COLOR_SAFE_ZONE_A = (80, 150, 255, 120)  # Bright blue with transparency
COLOR_SAFE_ZONE_B = (255, 120, 80, 120)  # Bright orange with transparency

COLOR_HOOP_A = (100, 200, 255)  # Cyan
COLOR_HOOP_B = (255, 150, 50)  # Orange

COLOR_JAIL_A = (120, 120, 120)
COLOR_JAIL_B = (120, 120, 120)

COLOR_PLAYER_A = (50, 100, 255)  # Bright blue
COLOR_PLAYER_A_CARRIER = (50, 255, 100)  # Bright green when carrying pin
COLOR_PLAYER_B = (255, 60, 60)  # Bright red
COLOR_PLAYER_B_CARRIER = (255, 220, 50)  # Bright yellow when carrying pin

# Individual player colors for Team A (10 distinct blue shades)
TEAM_A_COLORS = [
    (30, 144, 255),   # Dodger Blue - Player 0
    (65, 105, 225),   # Royal Blue - Player 1
    (100, 149, 237),  # Cornflower Blue - Player 2
    (70, 130, 180),   # Steel Blue - Player 3
    (0, 191, 255),    # Deep Sky Blue - Player 4
    (135, 206, 250),  # Light Sky Blue - Player 5
    (176, 196, 222),  # Light Steel Blue - Player 6
    (95, 158, 160),   # Cadet Blue - Player 7
    (72, 209, 204),   # Medium Turquoise - Player 8
    (64, 224, 208),   # Turquoise - Player 9
]

# Individual player colors for Team B (10 distinct red/orange shades)
TEAM_B_COLORS = [
    (220, 20, 60),    # Crimson - Player 0
    (255, 69, 0),     # Orange Red - Player 1
    (255, 99, 71),    # Tomato - Player 2
    (255, 140, 0),    # Dark Orange - Player 3
    (255, 165, 0),    # Orange - Player 4
    (240, 128, 128),  # Light Coral - Player 5
    (250, 128, 114),  # Salmon - Player 6
    (233, 150, 122),  # Dark Salmon - Player 7
    (255, 160, 122),  # Light Salmon - Player 8
    (205, 92, 92),    # Indian Red - Player 9
]

COLOR_PIN = (255, 215, 0)  # Gold
COLOR_TEXT = (255, 255, 255)  # White text
COLOR_WHITE = (255, 255, 255)
COLOR_IMMUNITY_GLOW = (255, 255, 150)  # Yellow glow for immunity

# Fonts - INCREASED sizes
FONT_SIZE_LARGE = 28
FONT_SIZE_MEDIUM = 20
FONT_SIZE_SMALL = 16


# ========================== PYGAME RENDERER ===============================


class PygameRenderer:
    """Visual renderer using Pygame."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("🎮 Capture the Flag - AI Battle Arena 🎮")

        self.font_large = pygame.font.Font(None, FONT_SIZE_LARGE)
        self.font_medium = pygame.font.Font(None, FONT_SIZE_MEDIUM)
        self.font_small = pygame.font.Font(None, FONT_SIZE_SMALL)

        self.clock = pygame.time.Clock()
        self.running = True
        
        # Animation frame counter
        self.frame = 0
        
        # Track events for visual feedback
        self.last_capture = None  # (team_captured, position, frames_left)
        self.last_pin_pickup = None  # (team, position, frames_left)
        self.particles = []  # List of particle effects

    def handle_events(self) -> bool:
        """Process pygame events. Returns False if user wants to quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
        return True

    def render(self, state: GameState, last_move: Optional[str] = None):
        """Draw the complete game state with enhanced visuals."""
        self.frame += 1
        self.screen.fill(COLOR_BG)

        # Draw grid and zones
        self._draw_grid(state)
        self._draw_zones(state)

        # Draw game objects
        self._draw_hoops(state)
        self._draw_jails(state)
        self._draw_players(state)
        
        # Draw particle effects
        self._update_and_draw_particles()

        # Draw info panels
        self._draw_top_bar(state, last_move)
        self._draw_sidebar(state)
        
        # Draw border glow effect
        self._draw_border_glow()

        pygame.display.flip()

    def _grid_to_screen(self, row: int, col: int) -> tuple[int, int]:
        """Convert grid coordinates to screen pixel coordinates (top-left of cell)."""
        x = col * CELL_SIZE
        y = row * CELL_SIZE + 60  # Offset for top bar
        return x, y

    def _draw_grid(self, state: GameState):
        """Draw grid lines and territory backgrounds."""
        # Territory backgrounds
        midline = GRID_ROWS // 2

        # Team A territory (top)
        for row in range(midline + 1):
            for col in range(GRID_COLS):
                x, y = self._grid_to_screen(row, col)
                rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.screen, COLOR_TEAM_A_TERRITORY, rect)

        # Team B territory (bottom)
        for row in range(midline + 1, GRID_ROWS):
            for col in range(GRID_COLS):
                x, y = self._grid_to_screen(row, col)
                rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.screen, COLOR_TEAM_B_TERRITORY, rect)

        # Grid lines
        for row in range(GRID_ROWS + 1):
            y = row * CELL_SIZE + 60
            pygame.draw.line(
                self.screen,
                COLOR_GRID,
                (0, y),
                (GRID_COLS * CELL_SIZE, y),
                1,
            )

        for col in range(GRID_COLS + 1):
            x = col * CELL_SIZE
            pygame.draw.line(
                self.screen,
                COLOR_GRID,
                (x, 60),
                (x, GRID_ROWS * CELL_SIZE + 60),
                1,
            )

    def _draw_zones(self, state: GameState):
        """Draw safe zones as semi-transparent overlays."""
        # Create surface with per-pixel alpha
        overlay = pygame.Surface((GRID_COLS * CELL_SIZE, GRID_ROWS * CELL_SIZE), pygame.SRCALPHA)

        for team, rect in state.layout.safe_zones.items():
            color = COLOR_SAFE_ZONE_A if team is Team.A else COLOR_SAFE_ZONE_B
            x, y = self._grid_to_screen(rect.top, rect.left)
            width = rect.width * CELL_SIZE
            height = rect.height * CELL_SIZE
            pygame.draw.rect(overlay, color, (x, y - 60, width, height))

        self.screen.blit(overlay, (0, 60))

    def _draw_hoops(self, state: GameState):
        """Draw hula hoops."""
        for team, pos in state.layout.hula_hoops.items():
            x, y = self._grid_to_screen(pos.row, pos.col)
            center = (x + CELL_SIZE // 2, y + CELL_SIZE // 2)
            color = COLOR_HOOP_A if team is Team.A else COLOR_HOOP_B

            # Draw hoop as large circle
            pygame.draw.circle(self.screen, color, center, CELL_SIZE // 3, 3)

            # Draw pins at hoop (initial + captured - taken)
            pins = state.pins_at_hoop[team]
            text = self.font_small.render(f"{pins}", True, COLOR_TEXT)
            text_rect = text.get_rect(center=center)
            self.screen.blit(text, text_rect)

    def _draw_jails(self, state: GameState):
        """Draw jail cells."""
        for team, pos in state.layout.jail_cells.items():
            x, y = self._grid_to_screen(pos.row, pos.col)
            rect = pygame.Rect(x + 5, y + 5, CELL_SIZE - 10, CELL_SIZE - 10)
            pygame.draw.rect(self.screen, COLOR_JAIL_A, rect, 3)

            # Draw bars
            for i in range(3):
                bar_x = x + 10 + i * 10
                pygame.draw.line(
                    self.screen,
                    COLOR_JAIL_A,
                    (bar_x, y + 5),
                    (bar_x, y + CELL_SIZE - 5),
                    2,
                )

    def _draw_players(self, state: GameState):
        """Draw all players (both active and jailed) with pulsing animations."""
        # Draw jailed players at jail locations
        for team in [Team.A, Team.B]:
            jailed = state.jailed_players(team)
            if jailed:
                # Jailed players of team X appear at jail_cells[team], which is in opponent's territory
                # jail_cells[Team.A] is where Team A's jailed players are held (in Team B territory)
                jail_pos = state.layout.jail_cells[team]
                x, y = self._grid_to_screen(jail_pos.row, jail_pos.col)
                
                # Stack jailed players in jail cell
                for i, player in enumerate(jailed):
                    offset_x = (i % 3) * 15 + 10  # 3 per row
                    offset_y = (i // 3) * 15 + 10
                    center = (x + offset_x, y + offset_y)
                    
                    # Use individual player colors
                    if player.team is Team.A:
                        color = TEAM_A_COLORS[player.player_id]
                    else:
                        color = TEAM_B_COLORS[player.player_id]
                    
                    pygame.draw.circle(self.screen, color, center, 6)  # Small circles in jail
                    # Draw X over jailed player
                    pygame.draw.line(self.screen, (200, 200, 200), (center[0] - 4, center[1] - 4), 
                                   (center[0] + 4, center[1] + 4), 2)
                    pygame.draw.line(self.screen, (200, 200, 200), (center[0] - 4, center[1] + 4), 
                                   (center[0] + 4, center[1] - 4), 2)
        
        # Draw active players on field
        pulse = abs(math.sin(self.frame * 0.1))  # Pulsing animation
        
        # Group players by position to handle overlapping
        from collections import defaultdict
        players_by_pos = defaultdict(list)
        for player in state.players:
            if not player.jailed:
                players_by_pos[(player.position.row, player.position.col)].append(player)
        
        # Draw each group with offsets if multiple players at same position
        for (row, col), players_at_pos in players_by_pos.items():
            x, y = self._grid_to_screen(row, col)
            
            for idx, player in enumerate(players_at_pos):
                # Offset players if multiple at same position
                if len(players_at_pos) > 1:
                    offset_angle = (2 * 3.14159 * idx) / len(players_at_pos)
                    offset_dist = 20  # Increased from 12 for better visibility
                    offset_x = int(offset_dist * math.cos(offset_angle))
                    offset_y = int(offset_dist * math.sin(offset_angle))
                    center = (x + CELL_SIZE // 2 + offset_x, y + CELL_SIZE // 2 + offset_y)
                else:
                    center = (x + CELL_SIZE // 2, y + CELL_SIZE // 2)

                # Choose base color from individual player palette
                if player.team is Team.A:
                    base_color = TEAM_A_COLORS[player.player_id]
                    carrier_tint = (50, 255, 100)  # Green tint for carriers
                else:
                    base_color = TEAM_B_COLORS[player.player_id]
                    carrier_tint = (255, 220, 50)  # Yellow tint for carriers
                
                # Blend with carrier color if carrying
                if player.carrying_pin:
                    color = tuple((base_color[i] + carrier_tint[i]) // 2 for i in range(3))
                else:
                    color = base_color

                # Draw player as circle with pulsing effect for carriers
                base_radius = 18 if player.carrying_pin else 15
                radius = base_radius + int(pulse * 3) if player.carrying_pin else base_radius
                
                # Outer glow for carriers
                if player.carrying_pin:
                    for i in range(3):
                        glow_radius = radius + 3 * (3 - i)
                        glow_color = (color[0] // 2, color[1] // 2, color[2] // 2)
                        pygame.draw.circle(self.screen, glow_color, center, glow_radius, 2)
                
                    pygame.draw.circle(self.screen, color, center, radius)

                # Add glowing border if has rescue immunity
                if player.rescue_immunity:
                    immunity_pulse = abs(math.sin(self.frame * 0.2))
                    immunity_color = COLOR_IMMUNITY_GLOW
                    pygame.draw.circle(self.screen, immunity_color, center, radius + 4, 3)
                    pygame.draw.circle(self.screen, immunity_color, center, radius + 6 + int(immunity_pulse * 2), 1)

                # Draw colored circle behind player ID number
                id_bg_radius = 10
                id_bg_color = (30, 100, 255) if player.team is Team.A else (255, 60, 60)
                pygame.draw.circle(self.screen, id_bg_color, center, id_bg_radius)
                pygame.draw.circle(self.screen, COLOR_WHITE, center, id_bg_radius, 2)  # White border
                
                # Draw player ID number in white
                id_text = self.font_small.render(str(player.player_id), True, COLOR_WHITE)
                id_rect = id_text.get_rect(center=center)
                self.screen.blit(id_text, id_rect)

    def _draw_top_bar(self, state: GameState, last_move: Optional[str]):
        """Draw top information bar with gradient background."""
        # Gradient background
        for i in range(80):
            color_val = 40 + i
            pygame.draw.line(self.screen, (color_val // 2, color_val // 2, color_val), 
                           (0, i), (WINDOW_WIDTH, i))

        # Team indicators on left and right
        team_a_color = COLOR_PLAYER_A
        team_b_color = COLOR_PLAYER_B
        
        # Team A indicator
        pygame.draw.circle(self.screen, team_a_color, (30, 30), 20)
        a_text = self.font_large.render("A", True, COLOR_WHITE)
        a_rect = a_text.get_rect(center=(30, 30))
        self.screen.blit(a_text, a_rect)
        
        # Team B indicator
        pygame.draw.circle(self.screen, team_b_color, (WINDOW_WIDTH - 30, 30), 20)
        b_text = self.font_large.render("B", True, COLOR_WHITE)
        b_rect = b_text.get_rect(center=(WINDOW_WIDTH - 30, 30))
        self.screen.blit(b_text, b_rect)

        # Turn info in center
        turn_text = f"Turn {state.turn_count}"
        text = self.font_large.render(turn_text, True, COLOR_WHITE)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, 20))
        self.screen.blit(text, text_rect)
        
        # Current turn indicator
        current_text = f"Team {state.current_turn.value}'s turn"
        current_color = team_a_color if state.current_turn is Team.A else team_b_color
        text = self.font_medium.render(current_text, True, current_color)
        text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, 45))
        self.screen.blit(text, text_rect)

        # Last move
        if last_move:
            move_text = f"Last: {last_move}"
            text = self.font_small.render(move_text, True, (200, 200, 200))
            self.screen.blit(text, (70, 50))

    def _draw_sidebar(self, state: GameState):
        """Draw right sidebar with game stats."""
        sidebar_x = GRID_COLS * CELL_SIZE
        sidebar_rect = pygame.Rect(sidebar_x, 60, SIDEBAR_WIDTH, WINDOW_HEIGHT - 60)
        pygame.draw.rect(self.screen, (60, 60, 60), sidebar_rect)

        y_offset = 80

        # Team A stats
        self._draw_team_stats(Team.A, state, sidebar_x + 10, y_offset)
        y_offset += 150

        # Team B stats
        self._draw_team_stats(Team.B, state, sidebar_x + 10, y_offset)
        y_offset += 150

        # Legend
        self._draw_legend(sidebar_x + 10, y_offset)

    def _draw_team_stats(self, team: Team, state: GameState, x: int, y: int):
        """Draw stats for one team."""
        color = COLOR_PLAYER_A if team is Team.A else COLOR_PLAYER_B

        # Team label
        label = self.font_large.render(f"Team {team.value}", True, color)
        self.screen.blit(label, (x, y))
        y += 30

        # Stats
        active = len(state.active_players(team))
        jailed = len(state.jailed_players(team))
        pins_captured = state.pins_captured[team]
        pins_remaining = state.pins_at_hoop[team]
        carriers = state.carrier_count(team)

        stats = [
            f"Active: {active}",
            f"Jailed: {jailed}",
            f"Carriers: {carriers}",
            f"Score: {pins_captured}",
            f"Pins @ hoop: {pins_remaining}",
        ]

        for stat in stats:
            text = self.font_small.render(stat, True, COLOR_WHITE)
            self.screen.blit(text, (x + 10, y))
            y += 20

    def _draw_legend(self, x: int, y: int):
        """Draw legend explaining visual elements."""
        label = self.font_medium.render("Legend:", True, COLOR_WHITE)
        self.screen.blit(label, (x, y))
        y += 25

        legend_items = [
            ("Blue: Team A", COLOR_PLAYER_A),
            ("Green: A carrier", COLOR_PLAYER_A_CARRIER),
            ("Red: Team B", COLOR_PLAYER_B),
            ("Yellow: B carrier", COLOR_PLAYER_B_CARRIER),
            ("Glow: Immunity", COLOR_IMMUNITY_GLOW),
        ]

        for text_str, color in legend_items:
            # Draw color sample
            pygame.draw.circle(self.screen, color, (x + 10, y + 8), 8)

            # Draw text
            text = self.font_small.render(text_str, True, COLOR_WHITE)
            self.screen.blit(text, (x + 25, y))
            y += 20
    
    def _update_and_draw_particles(self):
        """Update and render particle effects."""
        # Update particles (fade out over time)
        self.particles = [(pos, color, life - 1) for pos, color, life in self.particles if life > 0]
        
        # Draw particles
        for pos, color, life in self.particles:
            alpha = int(255 * (life / 20.0))
            radius = int(5 * (life / 20.0))
            if radius > 0:
                pygame.draw.circle(self.screen, color, pos, radius)
    
    def _draw_border_glow(self):
        """Draw animated border glow effect."""
        glow_intensity = int(50 + 30 * abs(math.sin(self.frame * 0.05)))
        border_color = (glow_intensity, glow_intensity, glow_intensity + 50)
        
        # Draw border lines
        pygame.draw.rect(self.screen, border_color, (0, 80, GRID_COLS * CELL_SIZE, GRID_ROWS * CELL_SIZE), 3)

    def wait(self, milliseconds: int):
        """Wait for specified time while keeping window responsive."""
        pygame.time.wait(milliseconds)

    def close(self):
        """Clean up pygame."""
        pygame.quit()
