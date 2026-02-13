from flask import Flask, render_template, request, jsonify
from solver import PipsSolver, Constraint, ConstraintType
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/solve', methods=['POST'])
def solve_puzzle():
    # Get parameters from request
    data = request.json
    grid_size = data.get('grid_size', 4)
    
    # Create default constraints
    constraints = [
        Constraint(
            constraint_type=ConstraintType.EQUAL,
            region=[(0,0), (0,1), (1,0), (1,1)]
        )
    ]
    
    # Solve the puzzle
    solver = PipsSolver(grid_size=grid_size, constraints=constraints)
    solution = solver.solve()
    
    # Convert solution to JSON
    if solution:
        return jsonify({
            'solved': True,
            'solution': solver.get_solution_as_list()
        })
    else:
        return jsonify({
            'solved': False,
            'solution': None
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
