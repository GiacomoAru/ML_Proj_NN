
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
import pandas as pd
import random
import matplotlib.colors as mcolors
import plotly.express as px
import pathlib

sys.path.append(os.path.abspath('./'))
from ActivationFunctions import *
from NeuralNetwork import *


RANDOM_STATE = 69

# -- PLOT --
def multy_plot(datas, labels, title=None, scale='linear', ax=None):
    x = np.arange(0, len(datas[0])).tolist()

    if ax != None: plt.sca(ax=ax)
    for i, el in enumerate(datas):
        plt.plot(x, el, label=labels[i])

    plt.title(title)
    plt.grid()
    plt.legend()
    plt.yscale(scale)
    if ax == None: plt.show()

def multy_plot_3d(x, y, z, label, title):
    print('Tot points:', len(x[0]))
    color_list = list(mcolors.TABLEAU_COLORS)
    fig = plt.figure(figsize=plt.figaspect(0.5))
    fig.suptitle(title)

    for i in range(len(x)):
        ax = fig.add_subplot(1, 2, i + 1, projection='3d')
        # For each set of style and range settings, plot n random points in the box
        # defined by x in [23, 32], y in [0, 100], z in [zlow, zhigh].
        ax.scatter(x[i], y[i], z[i], marker='o', color=color_list[i])
        ax.set_xlabel(label[i][0])
        ax.set_ylabel(label[i][1])
        ax.set_zlabel(label[i][2])

    return fig

def interactive_3d_plot(dataframe, x_col, y_col, z_col, color_col, size_col=None, max_size=None, symbol_col=None):
    print('Tot points:', len(dataframe))
    fig = px.scatter_3d(dataframe, x=x_col, y=y_col, z=z_col,
                color=color_col, opacity=0.7, size=size_col, size_max=max_size, symbol=symbol_col)

    fig.update_layout(
        margin=dict(l=100, r=100, t=10, b=10),
        paper_bgcolor="LightSteelBlue",
    )
    return fig


# -- create data structures --
def create_dataset(n_items, n_input, input_range, output_functions, seed):
    random.seed(seed)

    n_output = len(output_functions)
    x = np.ndarray((n_items, n_input + n_output))

    for i in range(n_items):
        for l in range(n_input):
            x[i,l] = random.uniform(input_range[0], input_range[1])

        for l, fun in enumerate(output_functions):
            
            x[i, n_input + l] = fun(x[i][:n_input])
            #print(x[i][:n_input], fun(x[i][:n_input]), x[i, l])

    return pd.DataFrame(x, columns = ['input_' + str(i + 1) for i in range(n_input)] + ['output_' + str(i + 1) for i in range(n_output)])


def create_stratified_topology(layers, act_fun_list = None):

    orig_layers_len = len(layers)
    if act_fun_list == None:
        if orig_layers_len > 2:
            act_fun_list = [[None, []]] * layers[0] + [['sigmoid',[1]]] * sum(layers[1:-1]) + [['identity', []]] * layers[-1]
        else:
            act_fun_list = [[None, []]] * layers[0] + [['identity', []]] * layers[-1]

    index_unit = 0
    layers.append(0)
    top = {}

    for i in range(orig_layers_len):
        if i == 0: 
            unit_type = 'input_'
        elif i == orig_layers_len - 1: 
            unit_type = 'output_'
        else: 
            unit_type = 'hidden_'

        succ = [index_unit + layers[i] + l for l in range(layers[i + 1])]

        for j in range(layers[i]):
            unit_act_fun = act_fun_list[index_unit + j][0]
            act_args = act_fun_list[index_unit + j][1]

            top[index_unit + j] = [unit_type + str(i), unit_act_fun, act_args, succ]
        index_unit += layers[i]

    return top

def monk_to_csv():
    
    for j in range(1,4):
        datas_tr = {'input_1':[],
                'input_2':[],
                'input_3':[],
                'input_4':[],
                'input_5':[],
                'input_6':[],
                'output_1':[]}
        datas_ts = {'input_1':[],
                'input_2':[],
                'input_3':[],
                'input_4':[],
                'input_5':[],
                'input_6':[],
                'output_1':[]}
        
        for line in open(pathlib.Path(__file__).parent.parent.joinpath('data\\monks\\monks-' + str(j) + '.test')):
            line_divided = line.split(' ')[1:]
            datas_ts['output_1'].append(line_divided[0])
            for i in range(1,7):
                datas_ts['input_' + str(i)].append(line_divided[i])

        for line in open(pathlib.Path(__file__).parent.parent.joinpath('data\\monks\\monks-' + str(j) + '.train')):
            line_divided = line.split(' ')[1:]
            datas_tr['output_1'].append(line_divided[0])
            for i in range(1,7):
                datas_tr['input_' + str(i)].append(line_divided[i])

        df = pd.DataFrame(datas_tr)
        df.to_csv(pathlib.Path(__file__).parent.parent.joinpath('data\\monks_csv\\monks_tr_' + str(j) + '.csv'))
        df = pd.DataFrame(datas_ts)
        df.to_csv(pathlib.Path(__file__).parent.parent.joinpath('data\\monks_csv\\monks_ts_' + str(j) + '.csv'))

