#!/usr/bin/env python3
# coding: utf-8

import collections
import functools
import math
import numpy as np
import scipy as sp
import sklearn.cross_decomposition as sklCD

import IO
import model


MODEL = None
TRAIN_SET = None
TEST_SET = None
STATS = None


@functools.lru_cache(maxsize=32, typed=False)
def symbol(category=None):
    """Return a dictionary with keys: hex, marker.

       On unknown category the first record is returned as default.
    """
    records = (('#1F77B4', 'o'),  # blue,     circle
               ('#2CA02C', 'x'),  # green,    cross
               ('#D62728', '^'),  # red,      triangle_up
               ('#FF7F0E', 'D'),  # orange,   diamond
               ('#A00000', 's'),  # dark_red, square
               ('#FFD700', '*'),  # gold,     star


               ('#000000', '+'),  #           plus
               ('#000000', 'h'),  #           hexagon
               ('#000000', 'p'),  #           pentagon
               )
    index = 0
    if category in TRAIN_SET.categories:
        index = sorted(TRAIN_SET.categories).index(category) % len(records)
    return [dict(zip(('hex', 'marker'), rec)) for rec in records][index]


def update_global_model(value):
    """Set MODEL to value."""
    if isinstance(value, model.Model):
        global MODEL
        MODEL = value
    else:
        IO.Log.error('Wrong type in update_global_model() '
                     '({}).'.format(type(value)))


def update_global_train_set(value):
    """Set TRAIN_SET to value."""
    if isinstance(value, model.TrainingSet):
        global TRAIN_SET
        TRAIN_SET = value
    else:
        IO.Log.error('Wrong type in update_global_model() '
                     '({}).'.format(type(value)))


def update_global_test_set(value):
    """Set TEST_SET to value."""
    if isinstance(value, model.TestSet):
        global TEST_SET
        TEST_SET = value
    else:
        IO.Log.error('Wrong type in update_global_model() '
                     '({}).'.format(type(value)))


def update_global_statistics(value):
    """Set STATS to value."""
    if isinstance(value, model.Statistics):
        global STATS
        STATS = value
    else:
        IO.Log.error('Wrong type in update_global_model() '
                     '({}).'.format(type(value)))


def scatter_wrapper(ax, x_values, y_values, cat=None):
    """Draw a scatter plot using a different color/marker for each category."""
    ax.scatter(x=x_values, y=y_values,
               alpha=0.5,
               c=symbol(cat)['hex'],
               edgecolors=symbol(cat)['hex'],
               label=cat,
               # linewidth=0.1,
               marker=symbol(cat)['marker'],
               s=30)


def line_wrapper(ax, x_values, y_values, cat=None):
    """Draw a line plot using a different color for each category."""
    ax.plot(x_values, y_values,
            alpha=0.5,
            color=symbol(cat)['hex'],
            linestyle='solid',
            marker=symbol(cat)['marker'],
            markerfacecolor=symbol(cat)['hex'],
            markeredgecolor=symbol(cat)['hex'],
            markersize=5)


def scree(ax, x=False, y=False):
    """Plot the explained variance of the model for the x or y matrix.

       Raise ValueError if x and y does not differ.
    """
    if bool(x) == bool(y):
        raise ValueError('In plot.scree() x, y matrix flags must differ')

    eigen = MODEL.x_eigenvalues if x else MODEL.y_eigenvalues
    line_wrapper(ax, range(len(eigen)), eigen)

    ax.set_title('Scree plot for {}'.format('x' if x else 'y'))
    ax.set_xlabel('Principal component number')
    ax.set_ylabel('Eigenvalues')
    ax.set_xlim(-0.5, len(eigen))
    ax.set_ylim(-0.5, math.ceil(eigen[0]) + 0.5)


def cumulative_explained_variance(ax, x=False, y=False):
    """Plot the cumulative explained variance for the x or y matrix.

       Raise ValueError if x and y does not differ.
    """
    if bool(x) == bool(y):
        raise ValueError('In plot.explained_variance() x, y matrix flags '
                         'does not differ')

    explained_variance = model.explained_variance(MODEL, 'x' if x else 'y')
    line_wrapper(ax, range(len(explained_variance)),
                 np.cumsum(explained_variance))

    ax.set_title('Explained variance plot for {}'.format('x' if x else 'y'))
    ax.set_xlabel('Principal component number')
    ax.set_ylabel('Cumulative variance captured (%)')
    ax.set_xlim(-0.5, len(explained_variance))
    ax.set_ylim(max(-2, explained_variance[0] - 2), 102)


def inner_relations(ax, num):
    """Plot the inner relations for the chosen latent variable.

       Raise ValueError if num is greater than available latent variables.
    """
    if num > MODEL.nr_lv:
        raise ValueError('In plot.inner_relations() num of latent variables '
                         'is out of bounds')

    for i in range(MODEL.T.shape[0]):
        scatter_wrapper(ax, MODEL.T[i, num], MODEL.U[i, num],
                        TRAIN_SET.categorical_y[i])

    ax.set_title('Inner relation for LV {}'.format(num))
    ax.set_xlabel('t{}'.format(num))
    ax.set_ylabel('u{}'.format(num))


def biplot(ax, pc_a, pc_b, x=False, y=False, normalize=True):
    """Plot loadings and scores on pc_a, pc_b components for the x or y matrix.

       Setting normalize force axes ends to -1 and 1.

       Raise ValueError if x and y does not differ.
       Raise ValueError if pc_a and pc_b are the same component.
    """
    if bool(x) == bool(y):
        raise ValueError('In plot.biplot() x, y matrix flags must differ')
    if pc_a == pc_b:
        raise ValueError('Principal components must be different!')

    scores(ax, pc_a, pc_b, x=x, y=y, normalize=normalize)
    loadings(ax, pc_a, pc_b, x=x, y=y)

    ax.set_title('Biplot for {}'.format('x' if x else 'y'))
    ax.set_xlabel('LV{}'.format(pc_a + 1))
    ax.set_ylabel('LV{}'.format(pc_b + 1))


def scores(ax, pc_a, pc_b, x=False, y=False, normalize=False):
    """Plot the scores on the pc_a, pc_b components for the x or y matrix.

       Setting normalize force axes ends to -1 and 1.
       Points of each category have a different color/shape.

       Raise ValueError if x and y does not differ.
       Raise ValueError if pc_a and pc_b are the same component.
    """
    if bool(x) == bool(y):
        raise ValueError('In plot.scores() x, y matrix flags must differ')
    if pc_a == pc_b:
        raise ValueError('Principal components must be different!')

    pc_a, pc_b = min(pc_a, pc_b), max(pc_a, pc_b)

    scores_matrix = MODEL.T.copy() if x else MODEL.U.copy()

    scores_a, scores_b = scores_matrix[:, pc_a], scores_matrix[:, pc_b]
    if normalize:
        scores_a = scores_a / max(abs(scores_a))
        scores_b = scores_b / max(abs(scores_b))

    for n in range(scores_matrix.shape[0]):
        scatter_wrapper(ax, scores_a[n], scores_b[n],
                        TRAIN_SET.categorical_y[n])

    ax.set_title('Scores plot for {}'.format('x' if x else 'y'))
    ax.set_xlabel('LV{}'.format(pc_a + 1))
    ax.set_ylabel('LV{}'.format(pc_b + 1))
    ax.axvline(0, linestyle='dashed', color='black')
    ax.axhline(0, linestyle='dashed', color='black')
    if normalize:
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)
    else:
        ax.set_xlim(model.integer_bounds(MODEL.P, MODEL.T, pc_a))
        ax.set_ylim(model.integer_bounds(MODEL.P, MODEL.T, pc_b))

    handles, labels = ax.get_legend_handles_labels()
    by_label = collections.OrderedDict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys())


def loadings(ax, pc_a, pc_b, x=False, y=False):
    """Plot the loadings on the pc_a, pc_b components for the x or y matrix.

       Annotate every point with the corresponding variable name.

       Raise ValueError if x and y does not differ.
       Raise ValueError if pc_a and pc_b are the same component.
    """
    if bool(x) == bool(y):
        raise ValueError('In plot.loadings() x, y matrix flags must differ')
    if pc_a == pc_b:
        raise ValueError('Principal components must be different!')

    pc_a, pc_b = min(pc_a, pc_b), max(pc_a, pc_b)

    loadings_matrix = MODEL.P.copy() if x else MODEL.Q.copy()
    scatter_wrapper(ax, loadings_matrix[:, pc_a], loadings_matrix[:, pc_b])

    for n in range(loadings_matrix.shape[0]):
        ax.annotate(TRAIN_SET.header[n + 1],
                    horizontalalignment='center',
                    textcoords='offset points',
                    verticalalignment='bottom',
                    xy=(loadings_matrix[n, pc_a], loadings_matrix[n, pc_b]),
                    xycoords='data',
                    xytext=(0, 5))

    ax.set_title('Loadings plot for {}'.format('x' if x else 'y'))
    ax.set_xlabel('LV{}'.format(pc_a + 1))
    ax.set_ylabel('LV{}'.format(pc_b + 1))
    ax.axvline(0, linestyle='dashed', color='black')
    ax.axhline(0, linestyle='dashed', color='black')


def calculated_y(ax):
    """Plot the difference between the real categories and the modeled ones."""
    ax.set_title('Y calculated')
    ax.set_xlabel('sample')
    ax.set_ylabel('modeled Y')
    for j in range(MODEL.p):
        for i in range(MODEL.n):
            scatter_wrapper(ax, i, MODEL.Y_modeled[i, j],
                            TRAIN_SET.categorical_y[i])


def predicted_y(ax):
    raise NotImplementedError


def t_square_q(ax):
    """Plot the q statistic over the Hotelling's t^2 with confidence levels."""
    MODEL.nr_lv = 3
    ax.set_title('T^2 - Q')
    ax.set_xlabel('Hotelling\'s T^2')
    ax.set_ylabel('Q residuals')

    t_square = MODEL.t_square
    q_res = MODEL.q_residuals_x
    for i in range(MODEL.n):
        scatter_wrapper(ax, t_square[i], q_res[i], TRAIN_SET.categorical_y[i])

    t_square_confidence_level = sp.stats.norm.interval(0.95, np.mean(t_square),
                                                       np.std(t_square))[1]
    q_confidence_level = sp.stats.norm.interval(0.95, np.mean(q_res),
                                                np.std(q_res))[1]

    ax.axvline(t_square_confidence_level, linestyle='dashed', color='black')
    ax.axhline(q_confidence_level, linestyle='dashed', color='black')

    handles, labels = ax.get_legend_handles_labels()
    by_label = collections.OrderedDict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys())


def y_residuals_leverage(ax):
    """Plot Y residuals over the leverage."""
    temp = np.linalg.inv(np.dot(MODEL.U.T, MODEL.U))
    leverage = np.empty(MODEL.n)

    for j in range(MODEL.p):
        for i in range(MODEL.n):
            leverage[i] = MODEL.U[i].dot(temp).dot(MODEL.U[i].T)
            scatter_wrapper(ax, leverage[i], MODEL.E_y[i, j],
                            TRAIN_SET.categorical_y[i])

    ax.set_title('Leverage')
    ax.set_xlabel('leverage')
    ax.set_ylabel('Y residuals')


def leverage(ax):
    """Plot leverage over the sample."""
    temp = np.linalg.inv(np.dot(MODEL.U.T, MODEL.U))
    leverage = np.empty(MODEL.n)

    for i in range(MODEL.n):
        leverage[i] = MODEL.U[i].dot(temp).dot(MODEL.U[i].T)
        scatter_wrapper(ax, i, leverage[i],
                        TRAIN_SET.categorical_y[i])

    ax.set_title('Leverage')
    ax.set_xlabel('sample')
    ax.set_ylabel('leverage')


def regression_coefficients(ax):
    """Plot the regression coefficients."""
    for i in range(MODEL.b.shape[0]):
        scatter_wrapper(ax, i, MODEL.b[i], TRAIN_SET.categorical_y[i])

    ax.set_title('Inner relation (variable b)')
    ax.set_xlabel('LV number')
    ax.set_ylabel('inner relation variable')


def weights(ax, lv_a, lv_b):
    """Plot the weights regarding the given principal components.

       Annotate every point with the corresponding variable name.

       Raise ValueError if pc_a and pc_b are the same component.
    """
    if lv_a == lv_b:
        raise ValueError('Principal components must be different!')

    lv_a, lv_b = min(lv_a, lv_b), max(lv_a, lv_b)

    scatter_wrapper(ax, MODEL.W[:, lv_a], MODEL.W[:, lv_b])

    for n in range(MODEL.W.shape[0]):
        ax.annotate(TRAIN_SET.header[n + 1],
                    horizontalalignment='center',
                    textcoords='offset points',
                    verticalalignment='bottom',
                    xy=(MODEL.W[n, lv_a], MODEL.W[n, lv_b]),
                    xycoords='data',
                    xytext=(0, 5))

    ax.set_title('Weights plot')
    ax.set_xlabel('LV{}'.format(lv_a + 1))
    ax.set_ylabel('LV{}'.format(lv_b + 1))
    ax.axvline(0, linestyle='dashed', color='black')
    ax.axhline(0, linestyle='dashed', color='black')


def weights_line(ax, lv):
    """Plot all the weights used by the model."""
    line_wrapper(ax, range(MODEL.W.shape[0]), MODEL.W[:, lv])

    ax.set_title('Weights line plot')
    ax.set_xlabel('Sample')
    ax.set_ylabel('LV{}'.format(lv + 1))
    ax.axvline(0, linestyle='dashed', color='black')
    ax.axhline(0, linestyle='dashed', color='black')


def data(ax):
    """Plot the dataset distinguishing with colors the categories."""
    for i in range(MODEL.n):
        line_wrapper(ax, range(MODEL.m), TRAIN_SET.x[i],
                     TRAIN_SET.categorical_y[i])

    ax.set_title('Data by category')
    ax.set_xlabel('sample')
    ax.set_ylabel('Value')


def sklearn_inner_relations(ax, num):
    """Plot the inner relations for the chosen latent variable.

       WARNING: implementation uses sklearn PLS regression!

       Raise ValueError if num is greater than available latent variables.
    """
    if num > MODEL.nr_lv:
        raise ValueError('In sklearn_inner_relations() num of latent variables'
                         ' is out of bounds')

    X, Y = TRAIN_SET.x.copy(), TRAIN_SET.y.copy()
    sklearn_pls = sklCD.PLSRegression(n_components=min(MODEL.n, MODEL.m),
                                      scale=True, max_iter=1e4, tol=1e-6,
                                      copy=True)
    sklearn_pls.fit(X, Y)

    for i in range(MODEL.T.shape[0]):
        scatter_wrapper(ax, sklearn_pls.x_scores_[i, num],
                        sklearn_pls.y_scores_[i, num],
                        TRAIN_SET.categorical_y[i])

    ax.set_title('Inner relation for LV {} (sklearn)'.format(num))
    ax.set_xlabel('t{}'.format(num))
    ax.set_ylabel('u{}'.format(num))


if __name__ == '__main__':
    raise SystemExit('Please do not run that script, load it!')
