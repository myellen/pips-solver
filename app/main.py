from flask import Flask, render_template, request, jsonify
from solver import PipsSolver, Constraint, ConstraintType

app = Flask(__name__)

VALID_GRID_SIZES = {3, 4, 5, 6}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/solve', methods=['POST'])
def solve_puzzle():
    try:
        data = request.get_json(force=True) or {}
        grid_size = data.get('grid_size', 4)

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

        solver = PipsSolver(grid_size=grid_size, constraints=constraints)
        solved = solver.solve()

        if solved:
            return jsonify({'solved': True, 'solution': solver.get_solution_as_list()})
        else:
            return jsonify({'solved': False, 'solution': None})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
