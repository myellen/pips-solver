from enum import Enum, auto
from typing import List, Tuple, Union, Optional
import copy
import random

class ConstraintType(Enum):
    EQUAL = auto()
    NOT_EQUAL = auto()
    GREATER_THAN = auto()
    LESS_THAN = auto()
    SUM = auto()
    BLANK = auto()

class Domino:
    def __init__(self, left_dots: int, right_dots: int):
        self.left = left_dots
        self.right = right_dots
        self.orientation = 'horizontal'
    
    def __repr__(self):
        return f"Domino({self.left}|{self.right})"
    
    def rotate(self):
        self.left, self.right = self.right, self.left
        self.orientation = 'vertical' if self.orientation == 'horizontal' else 'horizontal'

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
        grid: List[List[Union[Domino, None]]]
    ) -> bool:
        if not PipsConstraintChecker._is_region_complete(constraint.region, grid):
            return True
        
        region_values = PipsConstraintChecker._get_region_values(constraint.region, grid)
        return PipsConstraintChecker._apply_constraint_logic(constraint, region_values)
    
    @staticmethod
    def _is_region_complete(
        region: List[Tuple[int, int]], 
        grid: List[List[Union[Domino, None]]]
    ) -> bool:
        return all(grid[x][y] is not None for x, y in region)
    
    @staticmethod
    def _get_region_values(
        region: List[Tuple[int, int]], 
        grid: List[List[Union[Domino, None]]]
    ) -> List[int]:
        values = []
        for x, y in region:
            domino = grid[x][y]
            values.extend([domino.left, domino.right])
        return values
    
    @staticmethod
    def _apply_constraint_logic(
        constraint: Constraint, 
        values: List[int]
    ) -> bool:
        match constraint.type:
            case ConstraintType.EQUAL:
                return len(set(values)) == 1
            case ConstraintType.NOT_EQUAL:
                return len(set(values)) == len(values)
            case ConstraintType.GREATER_THAN:
                return all(val > constraint.value for val in values)
            case ConstraintType.LESS_THAN:
                return all(val < constraint.value for val in values)
            case ConstraintType.SUM:
                return sum(values) == constraint.value
            case ConstraintType.BLANK:
                return True
            case _:
                raise ValueError(f"Unsupported constraint type: {constraint.type}")

class PipsSolver:
    def __init__(
        self, 
        grid_size: int, 
        constraints: List[Constraint]
    ):
        self.grid_size = grid_size
        self.grid = [[None for _ in range(grid_size)] for _ in range(grid_size)]
        self.constraints = constraints
        self.domino_pool = self._generate_domino_pool()
    
    def _generate_domino_pool(self) -> List[Domino]:
        dominoes = []
        for left in range(7):
            for right in range(left, 7):
                dominoes.append(Domino(left, right))
                if left != right:
                    dominoes.append(Domino(right, left))
        return dominoes
    
    def solve(self) -> Optional[List[List[Domino]]]:
        solution = self._backtrack()
        return solution
    
    def _backtrack(
        self, 
        domino_index: int = 0, 
        placed_dominoes: int = 0
    ) -> Optional[List[List[Domino]]]:
        if placed_dominoes == (self.grid_size * self.grid_size) // 2:
            return copy.deepcopy(self.grid)
        
        for i in range(domino_index, len(self.domino_pool)):
            domino = self.domino_pool[i]
            
            for orientation in ['horizontal', 'vertical']:
                domino.orientation = orientation
                
                for x in range(self.grid_size):
                    for y in range(self.grid_size):
                        if self._is_valid_placement(domino, (x, y)):
                            self.grid[x][y] = domino
                            
                            adjacent_x = x + 1 if orientation == 'horizontal' else x
                            adjacent_y = y + 1 if orientation == 'vertical' else y
                            
                            if (0 <= adjacent_x < self.grid_size and 
                                0 <= adjacent_y < self.grid_size and 
                                self._is_valid_placement(domino, (adjacent_x, adjacent_y))):
                                
                                self.grid[adjacent_x][adjacent_y] = domino
                                
                                result = self._backtrack(
                                    domino_index + 1, 
                                    placed_dominoes + 1
                                )
                                
                                if result:
                                    return result
                                
                                self.grid[adjacent_x][adjacent_y] = None
                            
                            self.grid[x][y] = None
        
        return None
    
    def _is_valid_placement(
        self, 
        domino: Domino, 
        position: Tuple[int, int]
    ) -> bool:
        x, y = position
        
        if x >= self.grid_size or y >= self.grid_size:
            return False
        
        if self.grid[x][y] is not None:
            return False
        
        for constraint in self.constraints:
            if not PipsConstraintChecker.check_constraint(constraint, self.grid):
                return False
        
        return True
    
    def get_solution_as_list(self):
        """Convert solution to a list of lists for JSON serialization"""
        if not self.grid:
            return None
        
        return [
            [
                {
                    'left': domino.left,
                    'right': domino.right,
                    'orientation': domino.orientation
                } if domino else None 
                for domino in row
            ] 
            for row in self.grid
        ]
