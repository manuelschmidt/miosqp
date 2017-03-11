"""
Solve MIQP using mathprogbasepy
"""
from __future__ import division
from __future__ import print_function
from builtins import range
import scipy as sp
import scipy.sparse as spa
import numpy as np
import numpy.linalg as la
import pandas as pd


import mathprogbasepy as mpbpy
import miosqp

 # Import progress bar
from tqdm import tqdm

# Reload miosqp module
try:
    reload  # Python 2.7
except NameError:
    from importlib import reload  # Python 3.4+

reload(miosqp)


def solve(n_vec, m_vec, p_vec, repeat, dns_level, seed, solver='gurobi'):
    """
    Solve random optimization problems
    """

    print("Solving random problems with solver %s\n" % solver)

    # Define statistics to record
    avg_solve_time = np.zeros(len(n_vec))
    min_solve_time = np.zeros(len(n_vec))
    max_solve_time = np.zeros(len(n_vec))

    if solver == 'miosqp':
        # Add OSQP solve times statistics
        avg_osqp_solve_time = np.zeros(len(n_vec))
        min_osqp_solve_time = np.zeros(len(n_vec))
        max_osqp_solve_time = np.zeros(len(n_vec))

    # reset random seed
    np.random.seed(seed)

    for i in range(n_prob):

        # Get dimensions
        n = n_vec[i]
        m = m_vec[i]
        p = p_vec[i]

        print("problem n = %i, m = %i, p = %i" % (n, m, p))

        # Define vector of cpu times
        solve_time_temp = np.zeros(repeat)

        if solver == 'miosqp':
            osqp_solve_time_temp = np.zeros(repeat)

        for j in tqdm(range(repeat)):

            # Generate random vector of indeces
            i_idx = np.random.choice(np.arange(0, n), p, replace=False)

            # Generate random Matrices
            Pt = spa.random(n, n, density=dns_level)
            P = spa.csc_matrix(np.dot(Pt.T, Pt))
            q = sp.randn(n)
            A = spa.random(m, n, density=dns_level)
            u = 1 + sp.rand(m)
            l = -1 + sp.rand(m)

            # Enforce [0, 1] bounds on variables
            A, l, u = miosqp.add_bounds(i_idx, 0., 1., A, l, u)

            if solver == 'gurobi':
                # Solve with gurobi
                prob = mpbpy.QuadprogProblem(P, q, A, l, u, i_idx)
                res_gurobi = prob.solve(solver=mpbpy.GUROBI, verbose=False)
                if res_gurobi.status != 'optimal':
                    import ipdb; ipdb.set_trace()
                solve_time_temp[j] = 1e3 * res_gurobi.cputime

            elif solver == 'miosqp':
                # Define problem settings
                miosqp_settings = {'eps_int_feas': 1e-03,   # integer feasibility tolerance
                                   'max_iter_bb': 1000,     # maximum number of iterations
                                   'tree_explor_rule': 1,   # tree exploration rule
                                                            #   [0] depth first
                                                            #   [1] two-phase: depth first  until first incumbent and then  best bound
                                   'branching_rule': 0,     # branching rule
                                                            #   [0] max fractional part
                                   'verbose': False,
                                   'print_interval': 1}

                osqp_settings = {'eps_abs': 1e-04,
                                 'eps_rel': 1e-04,
                                 'eps_inf': 1e-04,
                                 'rho': 0.005,
                                 'sigma': 0.01,
                                 'alpha': 1.5,
                                 'polish': False,
                                 'max_iter': 2000,
                                 'verbose': False}

                model = miosqp.MIOSQP()
                model.setup(P, q, A, l, u, i_idx,
                             miosqp_settings,
                             osqp_settings)
                res_miosqp = model.solve()

                if res_miosqp.status != miosqp.MI_SOLVED:
                    import ipdb; ipdb.set_trace()

                osqp_solve_time_temp[j] = 100 * (res_miosqp.osqp_solve_time / res_miosqp.run_time)
                solve_time_temp[j] = 1e3 * res_miosqp.run_time


        # Get time statistics
        avg_solve_time[i] = np.mean(solve_time_temp)
        max_solve_time[i] = np.max(solve_time_temp)
        min_solve_time[i] = np.min(solve_time_temp)

        if solver == 'miosqp':
            avg_osqp_solve_time[i] = np.mean(osqp_solve_time_temp)
            max_osqp_solve_time[i] = np.max(osqp_solve_time_temp)
            min_osqp_solve_time[i] = np.min(osqp_solve_time_temp)



    # Create pandas dataframe for the results
    df_dict = { 'n' : n_vec,
                'm' : m_vec,
                'p' : p_vec,
                't_min[ms]' : min_solve_time,
                't_max[ms]' : max_solve_time,
                't_avg[ms]' : avg_solve_time }

    if solver == 'miosqp':
        df_dict.update({'t_osqp_min[%]' : min_osqp_solve_time,
                        't_osqp_max[%]' : max_osqp_solve_time,
                        't_osqp_avg[%]' : avg_osqp_solve_time })

    timings = pd.DataFrame(df_dict)

    return timings




if __name__ == "__main__":

    # General settings
    n_repeat = 10               # Number of repetitions for each problem
    problem_set = 1             # Problem sets 1 (q << n) or 2 (q = n)
    density_level = 0.6         # density level for sparse matrices
    random_seed = 0              # set random seed to make results reproducible


    if problem_set == 1:
        n_arr = np.array([10, 10,  50, 50,  100, 100, 150, 150])
        m_arr = np.array([5,  100, 25, 200, 50,  200, 100, 300])
        p_arr = np.array([2,  2,   5,  10,  2,   15,  5,   20])

    # Other problems n = q
    elif problem_set == 2:
        n_arr = np.array([2, 4, 8, 12, 20, 25, 30, 35])
        m_arr = 5 * n_arr
        p_arr = n_arr

    n_prob = len(n_arr)                  # Number of problems in problem set


    timings_gurobi = solve(n_arr, m_arr, p_arr, n_repeat,
                           density_level, random_seed, solver='gurobi')

    timings_miosqp = solve(n_arr, m_arr, p_arr, n_repeat,
                           density_level, random_seed, solver='miosqp')


    print("\nResults GUROBI")
    print(timings_gurobi)

    print("\nResults MIOSQP")
    print(timings_miosqp)