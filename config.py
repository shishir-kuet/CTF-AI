"""Global configuration and layout helpers for the CTF adversarial search game."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Tuple


class Team(str, Enum):
	"""Enumerates the two competing teams."""

	A = "A"  # Upper half (MAX player / Minimax)
	B = "B"  # Lower half (MIN player / TBD AI)


# -- Core board sizing -----------------------------------------------------
GRID_ROWS: int = 9
GRID_COLS: int = 15
MIDLINE_ROW: int = GRID_ROWS // 2  # Integer split for odd grids

# -- Game object counts ----------------------------------------------------
TEAM_SIZE: int = 10
PINS_PER_TEAM: int = 3
HULA_HOOPS_PER_TEAM: int = 1  # Each hoop starts with all three pins
SAFE_ZONE_WIDTH: int = 3
SAFE_ZONE_HEIGHT: int = 3
MAX_PIN_CARRIERS_PER_TEAM: int = 1

# -- Turn & scoring constraints -------------------------------------------
MAX_TURNS: int = 300
MINIMAX_DEPTH_TEAM_A: int = 3

# -- Heuristic weights (mirrors written spec) -----------------------------
HEURISTIC_PIN_SCORE: int = 100
HEURISTIC_PLAYER_SCORE: int = 10
HEURISTIC_DISTANCE_WEIGHT: int = 1


@dataclass(frozen=True)
class Point:
	row: int
	col: int

	def translate(self, d_row: int, d_col: int) -> "Point":
		return Point(self.row + d_row, self.col + d_col)

	def in_bounds(self) -> bool:
		return 0 <= self.row < GRID_ROWS and 0 <= self.col < GRID_COLS


@dataclass(frozen=True)
class Rect:
	top: int
	left: int
	height: int
	width: int

	@property
	def bottom(self) -> int:
		return self.top + self.height - 1

	@property
	def right(self) -> int:
		return self.left + self.width - 1

	def contains(self, point: Point) -> bool:
		return (
			self.top <= point.row <= self.bottom
			and self.left <= point.col <= self.right
		)

	def cells(self) -> Iterable[Point]:
		for r in range(self.top, self.top + self.height):
			for c in range(self.left, self.left + self.width):
				yield Point(r, c)


@dataclass(frozen=True)
class Layout:
	safe_zones: Dict[Team, Rect]
	hula_hoops: Dict[Team, Point]
	jail_cells: Dict[Team, Point]
	release_points: Dict[Team, Point]


def _center_column(width: int) -> int:
	"""Return the left column that centers an object of `width` tiles."""

	return max(0, (GRID_COLS - width) // 2)


def _safe_zone_rect(top_row: int) -> Rect:
	return Rect(
		top=top_row,
		left=_center_column(SAFE_ZONE_WIDTH),
		height=SAFE_ZONE_HEIGHT,
		width=SAFE_ZONE_WIDTH,
	)


def build_default_layout() -> Layout:
	"""Create a symmetric layout that matches the rules agreed on with the user."""

	safe_zone_top = _safe_zone_rect(top_row=1)
	safe_zone_bottom = _safe_zone_rect(top_row=GRID_ROWS - SAFE_ZONE_HEIGHT - 1)

	hula_hoop_top = Point(row=1, col=GRID_COLS // 2)
	hula_hoop_bottom = Point(row=GRID_ROWS - 2, col=GRID_COLS // 2)

	# Each team's jail sits inside the opponent territory near the side edges
	jail_a = Point(row=GRID_ROWS - 2, col=1)  # Team A players are held here
	jail_b = Point(row=1, col=GRID_COLS - 2)  # Team B players are held here

	# Rescues teleport to the midline cell on their own side
	release_a = Point(row=MIDLINE_ROW - 1, col=GRID_COLS // 2)
	release_b = Point(row=MIDLINE_ROW, col=GRID_COLS // 2)

	return Layout(
		safe_zones={Team.A: safe_zone_top, Team.B: safe_zone_bottom},
		hula_hoops={Team.A: hula_hoop_top, Team.B: hula_hoop_bottom},
		jail_cells={Team.A: jail_a, Team.B: jail_b},
		release_points={Team.A: release_a, Team.B: release_b},
	)


DEFAULT_LAYOUT: Layout = build_default_layout()


def territory_rows(team: Team) -> Tuple[int, int]:
	"""Return inclusive row bounds for each team's territory."""

	if team is Team.A:
		return (0, MIDLINE_ROW)
	return (MIDLINE_ROW + 1, GRID_ROWS - 1)

