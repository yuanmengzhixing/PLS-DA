#!/usr/bin/env python3
# coding: utf-8

""" PLS-DA is a project about the Partial least squares Discriminant Analysis
    on a given dataset.'
    PLS-DA is a project developed for the Processing of Scientific Data exam
    at University of Modena and Reggio Emilia.
    Copyright (C) 2017  Serena Ziviani, Federico Motta
    This file is part of PLS-DA.
    PLS-DA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    any later version.
    PLS-DA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    You should have received a copy of the GNU General Public License
    along with PLS-DA.  If not, see <http://www.gnu.org/licenses/>.
"""

__authors__ = "Serena Ziviani, Federico Motta"
__copyright__ = "PLS-DA  Copyright (C)  2017"
__license__ = "GPL3"


import logging
import os
import numpy as np
import utility
import yaml

import plot
import model


if __name__ == '__main__':
    raise SystemExit('Please do not run that script, load it!')


def dump(workspace, split, sample):
    """Save the informations necessary to rebuild the model."""
    folder = os.path.abspath(workspace)
    if not os.path.isdir(folder):
        raise FileNotFoundError('Directory {} does not exist'.format(folder))

    train_set = plot.TRAIN_SET

    matrix = train_set.body.copy()
    matrix.insert(0, train_set.header)
    save_matrix(matrix, filename=os.path.join(folder, 'dataset.csv'))

    data = {'nr_lv': plot.MODEL.nr_lv, 'centered': train_set.centered,
            'normalized': train_set.normalized,
            'split': split, 'sample': sample}
    with open(os.path.join(folder, 'data.yaml'), 'w') as f:
        yaml.safe_dump(data, f)


def save_matrix(matrix, filename, header='', scientific_notation=False):
    """Save on CSV the specified matrix."""
    filename = os.path.abspath(filename)
    folder = os.path.split(filename)[0]
    if not os.path.isdir(folder):
        raise FileNotFoundError('Directory {} does not exist'.format(folder))
    np.savetxt(filename, matrix,
               '%s' if not scientific_notation else '%+15.9e',
               ';', header=header)


def load(workspace):
    """Load from workspace the informations necessary to rebuild the model.

       Return: (plsda_model, train_set, split, samples)
    """
    folder = os.path.abspath(workspace)
    if not os.path.isdir(folder):
        raise FileNotFoundError('Directory {} does not exist'.format(folder))

    with open(os.path.join(folder, 'data.yaml'), 'r') as f:
        data = yaml.safe_load(f)

    dataset = model.TrainingSet(os.path.join(folder, 'dataset.csv'))
    if data['centered']:
        dataset.center()
    if data['normalized']:
        dataset.normalize()

    nipals_model = model.nipals(dataset.x, dataset.y)
    nipals_model.nr_lv = data['nr_lv']

    return nipals_model, dataset, data['split'], data['sample']


def mat2str(data, h_bar='-', v_bar='|', join='+'):
    """Return an ascii table."""
    try:
        if isinstance(data, (np.ndarray, np.generic)) and data.ndim == 2:
            ret = join + h_bar + h_bar * 11 * len(data[0]) + join + '\n'
            for row in data:
                ret += v_bar + ' '
                for col in row:
                    ret += '{: < 10.3e} '.format(col)
                ret += v_bar + '\n'
            ret += join + h_bar + h_bar * 11 * len(data[0]) + join
        elif (isinstance(data, (np.ndarray, np.generic))
              and data.ndim == 1) or isinstance(data, (list, tuple)):
            ret = join + h_bar + h_bar * 11 * len(data) + join + '\n'
            ret += v_bar + ' '
            for cell in data:
                ret += '{: < 10.3e} '.format(cell)
            ret += v_bar + '\n'
            ret += join + h_bar + h_bar * 11 * len(data) + join
        else:
            raise Exception('Not supported data type ({}) '
                            'in mat2str()'.format(type(data)))
    except Exception as e:
        Log.warning(e)
        ret = str(data)
    finally:
        return ret


class Log(object):

    __default = 'critical' if utility.CLI.args().quiet >= 3 else \
                'error' if utility.CLI.args().quiet == 2 else    \
                'warning' if utility.CLI.args().quiet == 1 else  \
                'debug' if utility.CLI.args().verbose else       \
                'info'
    __initialized = False
    __name = 'PLS_DA'

    @staticmethod
    def __log(msg='', data=None, level=None):
        """Print log message if above threshold."""
        if level is None:
            level = Log.__default

        if not Log.__initialized:
            logging_level = getattr(logging, Log.__default.upper())
            logging.basicConfig(format='[%(levelname)-8s] %(message)s',
                                level=logging_level)
            for l in logging.Logger.manager.loggerDict:
                logging.getLogger(l).setLevel(logging.INFO)

            # current script / package logging
            logging.getLogger(Log.__name).setLevel(logging_level)
            Log.__initialized = True

        logger = getattr(logging.getLogger(Log.__name), level)
        my_new_line = '\n[{:<8}]     '.format(level.upper())
        if data is None:
            logger(msg.replace('\n', my_new_line))
        else:
            if (isinstance(data, (np.ndarray, np.generic))
                    and data.ndim in (1, 2)) or \
                    isinstance(data, (list, tuple)):
                data = mat2str(data)
            else:
                data = yaml.dump(data, default_flow_style=False)
                data = data.replace('\n...', '').rstrip('\n')
            logger(msg.rstrip('\n') + my_new_line +
                   data.replace('\n', my_new_line))

    @staticmethod
    def critical(msg='', data=None):
        return Log.__log(msg=msg, data=data, level='critical')

    @staticmethod
    def debug(msg='', data=None):
        return Log.__log(msg=msg, data=data, level='debug')

    @staticmethod
    def error(msg='', data=None):
        return Log.__log(msg=msg, data=data, level='error')

    @staticmethod
    def info(msg='', data=None):
        return Log.__log(msg=msg, data=data, level='info')

    @staticmethod
    def set_level(level):
        if not isinstance(level, str):
            Log.error('Log.set_level() takes a string as argumenent, not a '
                      '{}'.format(type(level)))
            return
        if level not in ('critical', 'debug', 'error', 'info', 'warning'):
            Log.error('Bad level ({}) in Log.set_level()'.format(level))
            return
        Log.__default = level
        Log.__initialized = False

    @staticmethod
    def warning(msg='', data=None):
        return Log.__log(msg=msg, data=data, level='warning')


class CSV(object):

    @staticmethod
    def parse(filename, encoding='iso8859', separator=';'):
        """Return the header (list) and the body of a table (list of lists).

           Raises Exception on input error or on malformed content.
        """
        header, body = list(), list()
        try:
            with open(filename, 'r', encoding=encoding) as f:
                header = f.readline().strip('\n').split(separator)

                for line in f.readlines():
                    row = line.strip('\n').split(separator)
                    body.append(list(row))
        except IOError:
            raise Exception('File {} not existent, not readable '
                            'or corrupted.'.format(filename))
        else:
            if len(header) < 1 or len(body) < 1:
                raise Exception('Too few columns or rows in '
                                '{}'.format(filename))
            for i, row in enumerate(body):
                if len(row) != len(header):
                    raise Exception('Bad number of columns in '
                                    '{} body row'.format(i))

            for i, row in enumerate(body):
                for j, cell in enumerate(row):
                    try:
                        val = float(cell.replace(',', '.'))
                    except ValueError:
                        continue
                    else:
                        body[i][j] = val
        return header, body
