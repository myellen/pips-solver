import json as json_module
import urllib.error
import urllib.request
from datetime import date

from flask import Flask, render_template, request, jsonify
from solver import PipsSolver, Domino, Constraint, ConstraintType

app = Flask(__name__)

VALID_GRID_SIZES = {3, 4, 5, 6}

# Maps NYT constraint type strings to our ConstraintType enum names.
# Types not listed here (e.g. "empty") have no constraint and are skipped.
NYT_CONSTRAINT_TYPE_MAP = {
    'sum': 'SUM',
    'equals': 'EQUAL',
    'unequal': 'NOT_EQUAL',
    'greater': 'GREATER_THAN',
    'less': 'LESS_THAN',
    'blank': 'BLANK',
}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/fetch-nyt', methods=['GET'])
def fetch_nyt_puzzle():
    """Fetch a NYT Pips puzzle and return it in our solver format."""
    puzzle_date = request.args.get('date', date.today().isoformat())
    difficulty = request.args.get('difficulty', 'easy')

    if difficulty not in ('easy', 'medium', 'hard'):
        return jsonify({'error': 'difficulty must be easy, medium, or hard'}), 400

    url = f'https://www.nytimes.com/svc/pips/v1/{puzzle_date}.json'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            nyt_data = json_module.loads(resp.read())
    except urllib.error.HTTPError as e:
        return jsonify({'error': f'NYT API returned {e.code} for date {puzzle_date}'}), 502
    except Exception as e:
        return jsonify({'error': f'Failed to fetch puzzle: {e}'}), 502

    puzzle = nyt_data.get(difficulty)
    if not puzzle:
        return jsonify({'error': f'No {difficulty} puzzle for {puzzle_date}'}), 404

    # Collect all cells referenced in regions to determine the board shape
    regions = puzzle.get('regions', [])
    all_cells = set()
    for r in regions:
        for idx in r.get('indices', []):
            all_cells.add((idx[0], idx[1]))

    if not all_cells:
        return jsonify({'error': 'Puzzle has no cells'}), 400

    # Normalize to 0-based coordinates
    min_row = min(c[0] for c in all_cells)
    min_col = min(c[1] for c in all_cells)
    norm_cells = {(r - min_row, c - min_col) for r, c in all_cells}
    max_row = max(c[0] for c in norm_cells)
    max_col = max(c[1] for c in norm_cells)
    grid_size = max(max_row, max_col) + 1

    # Build constraints in our format
    constraints = []
    for r in regions:
        nyt_type = r.get('type', '')
        our_type = NYT_CONSTRAINT_TYPE_MAP.get(nyt_type)
        if our_type is None:
            continue  # skip unknown constraint types
        region_cells = [
            [idx[0] - min_row, idx[1] - min_col]
            for idx in r.get('indices', [])
        ]
        target = r.get('target')
        constraints.append({
            'type': our_type,
            'value': target,
            'region': region_cells,
        })

    # Build domino pool from the puzzle's specific domino list
    domino_pool = puzzle.get('dominoes', [])

    return jsonify({
        'puzzle_id': puzzle.get('id'),
        'print_date': nyt_data.get('printDate', puzzle_date),
        'difficulty': difficulty,
        'grid_size': grid_size,
        'active_cells': [list(c) for c in sorted(norm_cells)],
        'domino_pool': domino_pool,
        'constraints': constraints,
    })


@app.route('/solve', methods=['POST'])
def solve_puzzle():
    try:
        data = request.get_json(force=True) or {}
        grid_size = data.get('grid_size', 4)

        custom_pool = data.get('domino_pool')    # [[left, right], ...]
        active_cells_raw = data.get('active_cells')  # [[x, y], ...]

        # Only validate grid_size for standard (no custom pool/cells) requests
        if custom_pool is None and active_cells_raw is None:
            if not isinstance(grid_size, int) or grid_size not in VALID_GRID_SIZES:
                return jsonify({'error': f'grid_size must be one of {sorted(VALID_GRID_SIZES)}'}), 400
            if (grid_size * grid_size) % 2 != 0:
                return jsonify({'solved': False, 'solution': None,
                                'message': 'Grid has an odd number of cells and cannot be tiled by dominoes'})

        constraints = []
        for c in data.get('constraints', []):
            try:
                constraint_type = ConstraintType[c['type']]
                region = [tuple(pos) for pos in c.get('region', [])]
                value = c.get('value')
                constraints.append(Constraint(constraint_type, value, region))
            except (KeyError, TypeError):
                return jsonify({'error': f'Invalid constraint: {c}'}), 400

        domino_pool = None
        if custom_pool is not None:
            domino_pool = [Domino(pair[0], pair[1]) for pair in custom_pool]

        active_cells = None
        if active_cells_raw is not None:
            active_cells = {tuple(c) for c in active_cells_raw}

        solver = PipsSolver(
            grid_size=grid_size,
            constraints=constraints,
            domino_pool=domino_pool,
            active_cells=active_cells,
        )
        solved = solver.solve()

        if solved:
            return jsonify({'solved': True, 'solution': solver.get_solution_as_list()})
        else:
            return jsonify({'solved': False, 'solution': None})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
