from ast import Raise
from email import header
from operator import index
from matplotlib.pylab import f
from pathlib import Path
import numpy as np
import math
import multiprocessing
import pandas
import itertools
import csv
import os
import ast
import json

from MyProcess import *

from NeuralNetwork import NeuralNetwork
import ErrorFunctions


#TODO implementare il ripristino (il main ricomputerà le configurazioni eliminando quelle già eseguite e salvate nei backup.)
#                                   le restanti saranno ridistribuite trai processi)
#TODO (opzionale) ottimizzare


class ModelSelection:
    '''
    Implementation of the model selection algorithm
    
    Attributes:
    -----------
    backup_file: file
        file to backup the model selection's state

    '''

    def kf_train(model, data_set:np.ndarray, k:int, metrics:list, model_args:list):
        '''
        Compute the Backpropagation training algorithm on the NN for given a data set, estimating the hyperparameter performances
        trough validation in k folds of the data
        
        param data_set: a set of samples (pattern-target pairs) for supervised learning
        param k: number of data folds (data splits)
        param batch_size: parameter which determines the amount of training samples consumed in each iteration of the algorithm
            -> 1: Online
            -> 1 < batch_size < len(TR): Minibatch with minibatch size equals to batch_size
            -> len(TR): Batch
        param max_epochs: the maximum number of epochs (consumption of the whole training set) on which the algorithm will iterate
        param error_function: a string indicating the error function that the algorithm whould exploit when calculating the error distances between iterations
            -> "mee": Mean Euclidean Error
            -> "lms": Least Mean Square
        param error_decrease_tolerance: the errors difference (gain) value that the algorithm should consider as sufficiently low in order to stop training 
        param patience: the number of epochs to wait when a "no more significant error decrease" occurs
        param learning_rate: Eta hyperparameter to control the learning rate of the algorithm
        param lambda_tikhonov: Lambda hyperparameter to control the learning algorithm complexity (Tikhonov Regularization / Ridge Regression)
        param alpha_momentum: Momentum Hyperparameter

        return: mean and variance of the validation error
        '''
        
        # Computation of the size of each split
        data_len = len(data_set)
        split_size = math.floor(data_len/k)
        
        val_errors = np.empty((k, len(metrics)))
        stats = {}
        split_index = 0
        
        
        #training_set = np.append(data_set[:split_index], data_set[split_index + split_size:], axis=0)
        #validation_set = data_set[split_index : split_index + split_size]
        
        
        # At each iteration only one of the K subsets of data is used as the validation set, 
        # while all others are used for training the model validated on it.
        for i in range(k):
            split_index += split_size
            model.reset_weights() # reset of the network to proceeds towards the next training (next fold)
            training_set = np.append(data_set[:split_size*i], data_set[split_size*(i + 1):], axis=0)
            validation_set = data_set[split_size*i : split_size*(i + 1)]
            
            new_stats = model.train(training_set, validation_set, *model_args)
            if not stats: # first iteration
                for key in model.input_stats:
                    stats[key] = new_stats[key]
                for key in model.train_stats:
                    stats[key] = [new_stats[key]]
                for mes in metrics:
                    stats['training_' + mes.__name__] = [new_stats['training_' + mes.__name__]]
                    stats['validation_' + mes.__name__] = [new_stats['validation_' + mes.__name__]]
                    # batch stats
                    stats['training_batch_' + mes.__name__] = [new_stats['training_batch_' + mes.__name__]]
                    stats['validation_batch_' + mes.__name__] = [new_stats['validation_batch_' + mes.__name__]]
            else: # other iterations
                for key in model.train_stats:
                    stats[key].append(new_stats[key])
                for mes in metrics:
                    stats['training_' + mes.__name__].append(new_stats['training_' + mes.__name__])
                    stats['validation_' + mes.__name__].append(new_stats['validation_' + mes.__name__])
                    # batch stats
                    stats['training_batch_' + mes.__name__].append(new_stats['training_batch_' + mes.__name__])
                    stats['validation_batch_' + mes.__name__].append(new_stats['validation_batch_' + mes.__name__])
                        
            for j, met in enumerate(metrics):
                val_errors[i, j] = met(model.predict_array(validation_set[:,:model.input_size]), validation_set[:,model.input_size:])
        
        stats['mean_metrics'] = np.mean(val_errors, axis=0)
        stats['variance_metrics'] = np.var(val_errors, axis=0)
        return stats

    def __init__(self, cv_backup:str):
        '''
        Constructor of the class
        
        param cv_backup: file to backup the model selection's state
        
        return: -
        ''' 
        if cv_backup is not None:
            if cv_backup.endswith('.csv'):
                self.backup = cv_backup
            else:
                Raise(ValueError(' cv_backup extension must be .csv'))
                
        else:
            Raise(ValueError('Backup file missing'))
            
        self.partials_backup_prefix = 'tmp_'
        self.partials_backup_path = '..\\data\\gs_data\\partial'
        self.backup = cv_backup
        self.default_values =  {
        'range_min' : -0.75,
        'range_max' : 0.75,
        'fan_in' : True,
        'random_state' : None,

        'lambda_tikhonov' : 0.0,
        'alpha_momentum' : 0.5,
        'learning_rate' : 0.1,
        'batch_size' : 1,
        'max_epochs' : 100,
        'error_decrease_tolerance' : 0.0001,
        'patience' : 10,
        'min_epochs' : 0,
        'metrics':[ErrorFunctions.mean_squared_error, ],
        
        'topology': {}, # must be inizialized

        'collect_data':False, 
        'collect_data_batch':False, 
        'verbose':False
        }
        self.inzialization_arg_names = ['topology', 'range_min', 'range_max', 'fan_in', 'random_state']
        self.train_arg_names = ['batch_size', 'max_epochs', 'error_decrease_tolerance', 'patience', 'min_epochs', 
                       'learning_rate', 'lambda_tikhonov', 'alpha_momentum', 'metrics', 'collect_data', 
                        'collect_data_batch', 'verbose']

    
    def __restore_backup(self, hyperparameters:list = None):
        '''
        Restore model selection's state from a backup file (csv format)

        param backup_file: backup file list to be used to restore the state
        
        return: -
        '''
        
        restore_file = self.__merge_csv_file(os.path.join(self.partials_backup_path, self.partials_backup_prefix + "0.csv"))
        
        csv = pandas.read_csv(restore_file)
        backup_hyperparameters = csv.columns.values.tolist()[:-1]
        
        if hyperparameters is not None:
            if backup_hyperparameters == hyperparameters: return None, False
        
        done_configurations = csv[csv.columns.difference(['stats'])].values.tolist()
        
        return done_configurations, True

    def __get_configurations(self, hyperparameters:dict, recovery:bool = False):
        '''
        Get all the possible configurations of the hyperparameters

        param hyperparameters: dictionary with the hyperparameters to be tested

        return: list of all the possible configurations and list of the hyperparameters' names
        '''
        done_configurations = []
        if recovery:
            done_configurations, success = self.__restore_backup(hyperparameters.keys())

            if not success:
                Raise(ValueError('The specified hyperparameters not correspond to backup data found'))
        
        configurations = []
        names = list(hyperparameters.keys())

        for hyper_param in hyperparameters:
            if hyper_param in self.default_values.keys():
                configurations.append(hyperparameters[hyper_param])

        configurations = [item for item in list(itertools.product(*configurations)) if list(item) not in done_configurations]

        return configurations, names

    def __merge_csv_file(self, results_file_name:str):
        '''
        Merge the results of the processes in a single file

        param results_file_name: name of the file obtained after the merge
        param n_proc: number of processes

        return: -
        '''
        
        backup_file = [f for f in os.listdir(self.partials_backup_path) if f.startswith(self.partials_backup_prefix)]

        backup_file = list(map(lambda f: os.path.join(self.partials_backup_path, f), backup_file))
        df = pandas.concat([pandas.read_csv(f, header = 0) for f in backup_file], ignore_index=True)
        
        for file in backup_file:
            os.remove(file)
            
        df.to_csv(results_file_name, index=False)

        return results_file_name

    def __train_modelKF(self, data_set:np.ndarray, hyperparameters:list, hyperparameters_name:list, 
                        k_folds:int = 1, backup:str = None, verbose:bool = True):
        '''
        Train the model with the given hyperparameters and the number of folds

        param dataset: dataset to be used for K-Fold cross validation
        param hyperparameters: dict of hyperparameters' configurations to be used for validation
        param hyperparameters_name: list of hyperparameters' names
        param k_folds: number of folds to be used in the cross validation
        param topology: topology of the neural network
        param backup: backup file to be used to write the results

        return: -

        '''   
        
        if not os.path.isfile(backup): 
            back_up = open(backup, 'a+') 
            writer = csv.writer(back_up)
            writer.writerow(hyperparameters_name + ['stats'])
        else: # if file exists i only add more data
            back_up = open(backup, 'a') 
            writer = csv.writer(back_up)

        # for every configuration create a new clean model and train it
        for configuration in hyperparameters:
            grid_val = self.default_values.copy()
            for i, hyper_param in enumerate(configuration): 
                grid_val[hyperparameters_name[i]] = hyper_param

            # create a new model
            grid_val['topology'] = ast.literal_eval(grid_val['topology'])
            args_init = [grid_val[key] for key in self.inzialization_arg_names]
            nn = NeuralNetwork(*args_init)
            # train the model
            args_train = [grid_val[key] for key in self.train_arg_names] 
            if verbose: print("Training a new model : ", args_train) # TODO: magari un contatore?
            
            
            
            stats = ModelSelection.kf_train(nn, data_set, k_folds, grid_val['metrics'], args_train) # TODO: metrics!?!?!?!?
            
            # TODO: se ci piace ottimizzare anche le nostre madri
            # potremmo accumulare un po di dati alla volta e poi scrverli tutti assieme ma non so se ha senso
            # back_up = open(backup, 'a') 
            # writer = csv.writer(back_up)
            writer.writerow(list(configuration) + [stats]) 
            back_up.flush()

        back_up.close()

    def grid_searchKF(self, data_set:np.ndarray, hyperparameters:dict = {}, k_folds:int = 2, n_proc:int = 1, recovery:bool = False):
        '''
        Implementation of the grid search algorithm

        param data_set: training set to be used in the grid search
        param hyperparameters: dictionary with the hyperparameters to be tested
        param k_folds: number of folds to be used in the cross validation
        param topology: topology of the neural network
        param topology_name: name of the network topology
        param n_proc: number of processes to be used in the grid search

        return: the best hyperparameters' configuration
        '''
        
        hyperparameters = dict(sorted(hyperparameters.items()))
        configurations, names = self.__get_configurations(hyperparameters, recovery)

        if n_proc == 1: # sequential execution
            self.__train_modelKF(data_set, configurations, names, k_folds, self.backup)
            return

        remainder = len(configurations) % n_proc
        single_conf_size = int(len(configurations) / n_proc)
        start = end = 0
        j = 0
        proc_pool = []
        partial_data_dir = Path(self.partials_backup_path).absolute()

        if not os.path.exists(partial_data_dir):
            os.makedirs(partial_data_dir)

        for i in range(n_proc): # distribute equally the workload among the processes
            start = end
            if remainder > 0:
                end += single_conf_size + 1
            else:
                end += single_conf_size
            
            j = i+1
            process = multiprocessing.Process(target=self.__train_modelKF, args=(data_set, configurations[start:end],
                                                                                 names, k_folds, os.path.join(partial_data_dir, f''+ self.partials_backup_prefix +f'{j}.csv')))
            proc_pool.append(process)
            process.start()
            
            remainder -= 1
           
        for process in proc_pool: # join all the terminated processes
            process.join()

        self.__merge_csv_file(self.backup)
    
    def __train_modelHO(self, training_set:np.ndarray, validation_set:np.ndarray, hyperparameters:list, 
                        hyperparameters_name:list, topology:dict = {}, topology_name:str = 'standard', 
                        backup:str = None):
        
        '''
        Train the model with the given configuration of hyperparameters

        param training_set: training set to be used for hold out validation
        param validation_set: validation set to be used for hold out validation
        param hyperparameters: list of hyperparameters' configurations to be used for validation
        param hyperparameters_name: list of hyperparameters' names
        param topology: topology of the neural network
        param topology_name: name of the topology
        param lock: lock to be used to write on the backup file
        param: backup: backup file

        return: -
        '''
        
        values_to_use = {
        'range_min' : -0.75,
        'range_max' : 0.75,
        'fan_in' : True,
        'random_state' : None,

        'lambda_tikhonov' : 0.0,
        'alpha_momentum' : 0.5,
        'learning_rate' : 0.1,
        'batch_size' : 1,
        'max_epochs' : 100,
        'error_decrease_tolerance' : 0.0001,
        'patience' : 10,
        'min_epochs' : 0,
        'metrics':[ErrorFunctions.mean_squared_error, ],

        'collect_data':True, 
        'collect_data_batch':False, 
        'verbose':False
        }
        inzialization_arg_names = ['range_min', 'range_max', 'fan_in', 'random_state']
        train_arg_names = ['batch_size', 'max_epochs', 'error_decrease_tolerance', 'patience', 'min_epochs', 
                       'learning_rate', 'lambda_tikhonov', 'alpha_momentum', 'metrics', 'collect_data', 
                        'collect_data_batch', 'verbose']

        if os.path.isfile(backup):
            back_up = open(backup, 'a')
            writer = csv.writer(back_up)
        else:
            back_up = open(backup, 'w+')
            writer = csv.writer(back_up)
            writer.writerow(hyperparameters_name + ['topology', 'validation_error_mean', 'validation_error_variance'])

        # for every configuration create a new clean model and train it
        for configuration in hyperparameters:
            '''for index, hyper_param in enumerate(configuration):
                if hyperparameters_name[index] == 'lambda_tikhonov':
                    lambda_tikhonov = hyper_param

                elif hyperparameters_name[index] == 'alpha_momentum':
                    alpha_momentum = hyper_param

                elif hyperparameters_name[index] == 'learning_rate':
                    learning_rate = hyper_param

                elif hyperparameters_name[index] == 'batch_size':
                    batch_size = hyper_param
                
                elif hyperparameters_name[index] == 'max_epochs':
                    max_epochs = hyper_param

                elif hyperparameters_name[index] == 'error_decrease_tolerance':
                    error_decrease_tolerance = hyper_param

                elif hyperparameters_name[index] == 'patience':
                    patience = hyper_param

                elif hyperparameters_name[index] == 'min_epochs':
                    min_epochs = hyper_param'''
            grid_val = self.default_values.copy()
            for i, key in enumerate(hyperparameters_name): grid_val[key] = configuration[i]

            # create a new model
            args_init = [grid_val[key] for key in inzialization_arg_names]
            nn = NeuralNetwork(topology, *args_init)
            # train the model
            args_train = [grid_val[key] for key in train_arg_names]
            

            stats = nn.ho_train(training_set, validation_set, *args_train)      
            writer.writerow(list(configuration) + [topology_name, stats['validation_mean_squared_error'][-1], 0])
            back_up.flush()

    def grid_searchHO(self, training_set:np.ndarray, validation_set:np.ndarray, hyperparameters:dict, 
                      topology:dict, n_proc:int = 1, topology_name:str = 'standard'):
        '''
        Implementation of the grid search algorithm using hold out validation

        param training_set: training set to be used in the grid search
        param validation_set: validation set to be used in the grid search
        param hyperparameters: dictionary with the hyperparameters to be tested
        param topology: topology of the neural network
        param n_proc: number of processes to be used in the grid search
        param topology_name: name of the network topology

        return: the best hyperparameters' configuration
        
        '''
        #TODO: ottimizzare caso con singolo processo, chiama direttamente la funzione _train_modelHO
        configurations, names = self.__get_configurations(hyperparameters)

        remainder = len(configurations) % n_proc
        single_conf_size = int(len(configurations) / n_proc)
        start = end = 0
        proc_pool = []
        
        for i in range(n_proc): # distribute equally the workload among the processes
            start = end
            if remainder > 0:
                end += single_conf_size + 1
            else:
                end += single_conf_size
            
            process = multiprocessing.Process(target=self.__train_modelHO, args=(training_set, validation_set, configurations[start:end],
                                                                                 names, topology, topology_name,
                                                                                 f'backup_{i}.csv',))
            proc_pool.append(process)
            process.start()
            
            remainder -= 1
           
        for process in proc_pool: # join all the terminated processes
            process.join()

        self.__merge_csv_file(self.backup, n_proc)
