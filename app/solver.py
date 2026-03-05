from enum import Enum, auto
from typing import List, Tuple, Union, Optional


class ConstraintType(Enum):
    EQUAL = auto()
    NOT_EQUAL = auto()
    GREATER_THAN = auto()
    LESS_THAN = auto()
    SUM = auto()
    BLANK = auto()


class Domino:
    def __init__(self, left: int, right: int):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Domino({self.left}|{self.right})"


class Constraint:
    def __init__(
        self,
        constraint_type: ConstraintType,
        value: Union[int, None] = None,
        region: List[Tuple[int, int]] = None
    ):
        self.type = constraint_type
        self.value = value
        self.region = region or []


class PipsConstraintChecker:
    @staticmethod
    def check_constraint(
        constraint: Constraint,
        pip_grid: List[List[Union[int, None]]]
    ) -> bool:
        # Only evaluate once the region is fully filled
        if not all(pip_grid[x][y] is not None for x, y in constraint.region):
            return True

        values = [pip_grid[x][y] for x, y in constraint.region]

        match constraint.type:
            case ConstraintType.EQUAL:
                return len(set(values)) == 1
            case ConstraintType.NOT_EQUAL:
                return len(set(values)) == len(values)
            case ConstraintType.GREATER_THAN:
                return all(v > constraint.value for v in values)
            case ConstraintType.LESS_THAN:
                return all(v < constraint.value for v in values)
            case ConstraintType.SUM:
                return sum(values) == constraint.value
            case ConstraintType.BLANK:
                return all(v == 0 for v in values)
            case _:
                raise ValueError(f"Unsupported constraint type: {constraint.type}")


class PipsSolver:
    def __init__(
        self,
        grid_size: int,
        constraints: List[Constraint],
        domino_pool: Optional[List[Domino]] = None,
        active_cells: Optional[set] = None,
    ):
        self.grid_size = grid_size
        self.constraints = constraints
        self.domino_pool = domino_pool if domino_pool is not None else self._generate_domino_pool()
        # pip_grid[x][y] = pip value (0-6), -1 for inactive cells, or None for empty
        self.pip_grid: List[List[Union[int, None]]] = [
            [None] * grid_size for _ in range(grid_size)
        ]
        # placement_grid[x][y] = (domino_idx, orientation, is_first) or None
        self.placement_grid: List[List[Union[tuple, None]]] = [
            [None] * grid_size for _ in range(grid_size)
        ]
        self.used = [False] * len(self.domino_pool)
        # Pre-fill inactive (hole) cells so the solver skips them
        if active_cells is not None:
            for x in range(grid_size):
                for y in range(grid_size):
                    if (x, y) not in active_cells:
                        self.pip_grid[x][y] = -1

    def _generate_domino_pool(self) -> List[Domino]:
        dominoes = []
        for left in range(7):
            for right in range(left, 7):
                dominoes.append(Domino(left, right))
        return dominoes

    def _first_empty(self) -> Optional[Tuple[int, int]]:
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                if self.pip_grid[x][y] is None:
                    return (x, y)
        return None

    def _constraints_ok(self) -> bool:
        for c in self.constraints:
            if not PipsConstraintChecker.check_constraint(c, self.pip_grid):
                return False
        return True

    def _backtrack(self) -> bool:
        cell = self._first_empty()
        if cell is None:
            return True  # all cells filled

        x, y = cell

        for i, domino in enumerate(self.domino_pool):
            if self.used[i]:
                continue

            # Try placing the domino horizontally (right) or vertically (down)
            for dx, dy, orientation in [(0, 1, 'horizontal'), (1, 0, 'vertical')]:
                x2, y2 = x + dx, y + dy

                if not (0 <= x2 < self.grid_size and 0 <= y2 < self.grid_size):
                    continue
                if self.pip_grid[x2][y2] is not None:
                    continue

                # Try both value orderings (left→right and right→left)
                orderings = [(domino.left, domino.right)]
                if domino.left != domino.right:
                    orderings.append((domino.right, domino.left))

                for v1, v2 in orderings:
                    self.pip_grid[x][y] = v1
                    self.pip_grid[x2][y2] = v2
                    self.placement_grid[x][y] = (i, orientation, True)
                    self.placement_grid[x2][y2] = (i, orientation, False)
                    self.used[i] = True

                    if self._constraints_ok() and self._backtrack():
                        return True

                    self.pip_grid[x][y] = None
                    self.pip_grid[x2][y2] = None
                    self.placement_grid[x][y] = None
                    self.placement_grid[x2][y2] = None
                    self.used[i] = False

        return False

    def solve(self) -> bool:
        return self._backtrack()

    def get_solution_as_list(self) -> Optional[List[List[dict]]]:
        result = []
        for x in range(self.grid_size):
            row = []
            for y in range(self.grid_size):
                v = self.pip_grid[x][y]
                p = self.placement_grid[x][y]
                if v is None or v == -1 or p is None:
                    row.append(None)
                else:
                    domino_idx, orientation, is_first = p
                    d = self.domino_pool[domino_idx]
                    row.append({
                        'value': v,
                        'left': d.left,
                        'right': d.right,
                        'domino_idx': domino_idx,
                        'orientation': orientation,
                        'is_first': is_first,
                    })
            result.append(row)
        return result
