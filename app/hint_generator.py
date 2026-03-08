"""Generate step-by-step hints for solving a Pips puzzle.

Given a solved grid and the puzzle constraints, this module produces an ordered
sequence of domino placements with teaching hints and explanations.
"""

from solver import Constraint, ConstraintType, Domino


# ---------------------------------------------------------------------------
# Hint text templates keyed by pattern name
# ---------------------------------------------------------------------------
HINT_TEMPLATES = {
    'blank_region': {
        'hint': 'Find the region marked BLANK. What must every cell be?',
        'explanation': 'A BLANK region means all cells are 0 pips. Place the {domino} domino here.',
    },
    'sum_0_2cell': {
        'hint': 'This 2-cell region sums to 0. What is the only possibility?',
        'explanation': 'Both halves must be 0, so the 0|0 domino goes here.',
    },
    'sum_12_2cell': {
        'hint': 'This 2-cell region sums to 12. What is the maximum pip value?',
        'explanation': '6 + 6 = 12, so this must be the 6|6 double domino.',
    },
    'gt5': {
        'hint': 'Every cell in this region must be greater than {value}. What is the only pip value that works?',
        'explanation': 'The only pip value greater than {value} is 6, so every cell here is 6.',
    },
    'lt1': {
        'hint': 'Every cell in this region must be less than {value}. What value works?',
        'explanation': 'The only pip value less than {value} is 0.',
    },
    'equal_2cell': {
        'hint': 'These 2 cells must be equal. What kind of domino has matching halves?',
        'explanation': 'Equal cells in a domino means it is a double. Both halves show {pip_value}.',
    },
    'equal_forced': {
        'hint': 'This EQUAL region needs {region_size} identical cells. Given the remaining dominoes, which value is possible?',
        'explanation': 'The only value that works here is {pip_value}, using the {domino} domino.',
    },
    'sum_unique_2cell': {
        'hint': 'This 2-cell region sums to {value}. Which remaining domino adds up to exactly {value}?',
        'explanation': 'Only the {domino} domino sums to {value}. Place it here.',
    },
    'sum_2cell': {
        'hint': 'This 2-cell region sums to {value}. Think about which pairs of pip values add up to {value}.',
        'explanation': '{val1} + {val2} = {value}, so the {domino} domino fits here.',
    },
    'not_equal': {
        'hint': 'Every cell in this region must be different. Consider what values are still available.',
        'explanation': 'By making all values unique, the {domino} domino fits here.',
    },
    'elimination': {
        'hint': 'Look at what dominoes are left and which cells are empty. Can you narrow it down?',
        'explanation': 'By process of elimination, the {domino} domino is the only one that works here.',
    },
    'general': {
        'hint': 'Consider the {constraint_desc} constraint on this region. What fits?',
        'explanation': 'The {domino} domino satisfies the constraint here.',
    },
}


def _domino_label(left, right):
    """Human-readable domino label like '3|5'."""
    return f'{left}|{right}'


def _constraint_description(constraint):
    """Short human label for a constraint, e.g. 'SUM 12'."""
    ctype = constraint.type
    val = constraint.value
    if ctype == ConstraintType.BLANK:
        return 'BLANK'
    if ctype == ConstraintType.EQUAL:
        return 'EQUAL'
    if ctype == ConstraintType.NOT_EQUAL:
        return 'ALL DIFFERENT'
    if ctype == ConstraintType.SUM:
        return f'SUM {val}'
    if ctype == ConstraintType.GREATER_THAN:
        return f'> {val}'
    if ctype == ConstraintType.LESS_THAN:
        return f'< {val}'
    return str(ctype.name)


# ---------------------------------------------------------------------------
# Extract domino placements from solved grid
# ---------------------------------------------------------------------------

def _extract_placements(solution, grid_size):
    """Return a list of unique domino placements from the solution grid.

    Each placement is a dict with:
        domino_idx, left, right, val1, val2, cell1, cell2, orientation
    """
    seen = set()
    placements = []
    for x in range(grid_size):
        for y in range(grid_size):
            cell = solution[x][y]
            if cell is None:
                continue
            didx = cell['domino_idx']
            if didx in seen:
                continue
            seen.add(didx)

            # Find the partner cell
            ori = cell['orientation']
            if cell['is_first']:
                cell1 = [x, y]
                val1 = cell['value']
                if ori == 'horizontal':
                    cell2 = [x, y + 1]
                else:
                    cell2 = [x + 1, y]
                val2 = solution[cell2[0]][cell2[1]]['value']
            else:
                val2 = cell['value']
                cell2 = [x, y]
                if ori == 'horizontal':
                    cell1 = [x, y - 1]
                else:
                    cell1 = [x - 1, y]
                val1 = solution[cell1[0]][cell1[1]]['value']

            placements.append({
                'domino_idx': didx,
                'left': cell['left'],
                'right': cell['right'],
                'val1': val1,
                'val2': val2,
                'cell1': cell1,
                'cell2': cell2,
                'orientation': ori,
            })
    return placements


# ---------------------------------------------------------------------------
# Build cell -> constraint mapping
# ---------------------------------------------------------------------------

def _build_cell_constraint_map(constraints):
    """Return dict mapping (x,y) -> list of Constraint objects."""
    mapping = {}
    for c in constraints:
        for cell in c.region:
            key = (cell[0], cell[1])
            mapping.setdefault(key, []).append(c)
    return mapping


# ---------------------------------------------------------------------------
# Find the best constraint for a given domino placement
# ---------------------------------------------------------------------------

def _find_domino_constraint(placement, cell_to_constraints):
    """Return the constraint that most tightly binds this domino's cells."""
    c1 = tuple(placement['cell1'])
    c2 = tuple(placement['cell2'])

    # Constraints that contain at least one of the domino's cells
    candidates = set()
    for c in cell_to_constraints.get(c1, []):
        candidates.add(id(c))
    for c in cell_to_constraints.get(c2, []):
        candidates.add(id(c))

    # Prefer constraints that contain BOTH cells, then smallest region
    all_constraints = cell_to_constraints.get(c1, []) + cell_to_constraints.get(c2, [])
    # Deduplicate
    seen_ids = set()
    unique = []
    for c in all_constraints:
        if id(c) not in seen_ids:
            seen_ids.add(id(c))
            unique.append(c)

    # Score each constraint for relevance
    best = None
    best_score = -1
    for c in unique:
        region_set = {(cell[0], cell[1]) for cell in c.region}
        both_in = c1 in region_set and c2 in region_set
        # Higher score = more relevant
        score = 0
        if both_in:
            score += 100
        if c.type == ConstraintType.BLANK:
            score += 50
        elif c.type == ConstraintType.SUM:
            score += 40
        elif c.type == ConstraintType.EQUAL:
            score += 35
        elif c.type == ConstraintType.GREATER_THAN:
            score += 30
        elif c.type == ConstraintType.LESS_THAN:
            score += 30
        elif c.type == ConstraintType.NOT_EQUAL:
            score += 20
        # Smaller regions are more constraining
        score += max(0, 20 - len(c.region))

        if score > best_score:
            best_score = score
            best = c

    return best


# ---------------------------------------------------------------------------
# Score how "deducible" a placement is (higher = easier to figure out)
# ---------------------------------------------------------------------------

def _score_placement(placement, constraint, domino_pool, used_set):
    """Return (score, pattern_name) for a placement."""
    if constraint is None:
        return 10, 'elimination'

    ctype = constraint.type
    cval = constraint.value
    region_size = len(constraint.region)
    c1 = tuple(placement['cell1'])
    c2 = tuple(placement['cell2'])
    region_set = {(cell[0], cell[1]) for cell in constraint.region}
    both_in = c1 in region_set and c2 in region_set

    # Pattern-specific scores only apply when BOTH domino cells are in the region.
    # When only one cell is in a region, the constraint alone doesn't determine the domino.
    if not both_in:
        if ctype == ConstraintType.BLANK:
            return 30, 'general'
        if ctype == ConstraintType.SUM:
            return 25, 'general'
        return 20, 'general'

    # BLANK region (both cells in region)
    if ctype == ConstraintType.BLANK:
        return 100, 'blank_region'

    # SUM with 2 cells (both cells of domino in the region)
    if ctype == ConstraintType.SUM and region_size == 2:
        if cval == 0:
            return 95, 'sum_0_2cell'
        if cval == 12:
            return 95, 'sum_12_2cell'
        # Check how many unused dominoes could produce this sum
        candidates = 0
        for i, d in enumerate(domino_pool):
            if i in used_set:
                continue
            if d.left + d.right == cval:
                candidates += 1
        if candidates == 1:
            return 85, 'sum_unique_2cell'
        return 50, 'sum_2cell'

    # GREATER_THAN 5 means all cells must be 6
    if ctype == ConstraintType.GREATER_THAN and cval is not None and cval >= 5:
        return 90, 'gt5'

    # LESS_THAN 1 means all cells must be 0
    if ctype == ConstraintType.LESS_THAN and cval is not None and cval <= 1:
        return 90, 'lt1'

    # EQUAL with 2 cells means double domino
    if ctype == ConstraintType.EQUAL and region_size == 2:
        return 85, 'equal_2cell'

    # EQUAL with larger region
    if ctype == ConstraintType.EQUAL:
        return 70, 'equal_forced'

    # SUM general (larger regions)
    if ctype == ConstraintType.SUM:
        return 45, 'sum_2cell'

    # NOT_EQUAL
    if ctype == ConstraintType.NOT_EQUAL:
        return 40, 'not_equal'

    # GREATER_THAN / LESS_THAN general
    if ctype in (ConstraintType.GREATER_THAN, ConstraintType.LESS_THAN):
        return 55, 'general'

    return 20, 'general'


# ---------------------------------------------------------------------------
# Generate hint and explanation text from a template
# ---------------------------------------------------------------------------

def _generate_text(pattern, placement, constraint):
    """Fill in template strings for the given pattern."""
    tmpl = HINT_TEMPLATES.get(pattern, HINT_TEMPLATES['general'])

    domino_label = _domino_label(placement['left'], placement['right'])
    fmt = {
        'domino': domino_label,
        'val1': placement['val1'],
        'val2': placement['val2'],
        'pip_value': placement['val1'],
        'value': constraint.value if constraint else '?',
        'region_size': len(constraint.region) if constraint else '?',
        'constraint_desc': _constraint_description(constraint) if constraint else 'this',
    }

    hint = tmpl['hint'].format_map(fmt)
    explanation = tmpl['explanation'].format_map(fmt)
    return hint, explanation


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_hints(solution, constraints, domino_pool, grid_size):
    """Generate an ordered list of hint steps for the solved puzzle.

    Parameters
    ----------
    solution : list[list[dict|None]]
        The solved grid from PipsSolver.get_solution_as_list().
    constraints : list[Constraint]
        The puzzle constraints.
    domino_pool : list[Domino]
        The domino pool used by the solver.
    grid_size : int
        Width/height of the grid.

    Returns
    -------
    list[dict]
        Ordered hint steps, each with hint text, explanation, cells, values, etc.
    """
    placements = _extract_placements(solution, grid_size)
    cell_to_constraints = _build_cell_constraint_map(constraints)

    # Score each placement
    scored = []
    used_set = set()
    for p in placements:
        constraint = _find_domino_constraint(p, cell_to_constraints)
        score, pattern = _score_placement(p, constraint, domino_pool, used_set)
        scored.append((score, p, pattern, constraint))

    # Sort: highest score first, then by top-left position for tie-breaking
    scored.sort(key=lambda x: (-x[0], x[1]['cell1'][0], x[1]['cell1'][1]))

    # Re-score with elimination awareness and generate text
    hints = []
    used_set = set()
    for i, (score, placement, pattern, constraint) in enumerate(scored):
        # Re-score now that we know which dominoes are "used" at this point
        if i > 0:
            new_score, new_pattern = _score_placement(
                placement, constraint, domino_pool, used_set
            )
            # If elimination makes it uniquely deducible, upgrade pattern
            if new_pattern == 'sum_unique_2cell' and pattern == 'sum_2cell':
                pattern = new_pattern

        hint_text, explanation = _generate_text(pattern, placement, constraint)

        # If we have used dominoes, mention it for context
        if used_set and pattern in ('sum_2cell', 'elimination', 'general', 'not_equal'):
            hint_text = (
                f'With {len(used_set)} domino{"s" if len(used_set) != 1 else ""} '
                f'already placed, {hint_text[0].lower()}{hint_text[1:]}'
            )

        used_set.add(placement['domino_idx'])

        hints.append({
            'step': i + 1,
            'hint': hint_text,
            'explanation': explanation,
            'pattern_name': pattern,
            'cells': [placement['cell1'], placement['cell2']],
            'values': [placement['val1'], placement['val2']],
            'domino_idx': placement['domino_idx'],
            'orientation': placement['orientation'],
            'constraint_type': constraint.type.name if constraint else None,
            'constraint_value': constraint.value if constraint else None,
            'constraint_region': (
                [[c[0], c[1]] for c in constraint.region] if constraint else None
            ),
        })

    return hints


def build_constraints_display(constraints):
    """Build a display-friendly list of constraints with labels.

    Returns list of dicts with type, value, region, and label fields.
    """
    display = []
    for c in constraints:
        display.append({
            'type': c.type.name,
            'value': c.value,
            'region': [[cell[0], cell[1]] for cell in c.region],
            'label': _constraint_description(c),
        })
    return display
