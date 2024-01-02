from ABCNeuron import ABCNeuron
from InputNeuron import InputNeuron
from HiddenNeuron import HiddenNeuron
from OutputNeuron import OutputNeuron
from ActivationFunctions import ActivationFunctions
import numpy


class NeuralNetwork:
    '''
    Implementation of the neural network that includes neurons and all method to use and train the NN
    
    Attributes
    ----------
    input_size: int
        the number of input units of the network
    output_size: int
        the number of output units of the network
    neurons: list of ABCNeuron
        the list of neurons, sorted in topological order, composing the NN
    
    '''

    def __get_function_from_string(self, name:str):
        '''
        Map the function name to the corresponding callable variable
        
        :param name: the name of the function to map
        :return: the function corrisponding to the name as a callable
        '''
        if name == 'identity':
            fun = ActivationFunctions.identity

        elif name == 'sigmoid':
            fun = ActivationFunctions.sigmoid

        elif name == 'tanh':
            fun = ActivationFunctions.tanh

        elif name == 'softplus':
            fun = ActivationFunctions.softplus

        elif name == 'gaussian':
            fun = ActivationFunctions.gaussian
        
        else:
            raise ValueError(f"Activation function {name} not found")

        return fun

    def __construct_from_dict(self, topology:dict, rand_range_min:float = -1, rand_range_max:float = 1, fan_in:bool = True):
        '''
        Builds a Neural Network of ABCNeuron's objects from the topology
        
        :param topology: the graph structure described by a dictionary (see __init__ comments)
        :param rand_range_min: minimum value for random weights initialisation range
        :param rand_range_max: maximum value for random weights initialisation range
        :param fan_in: if the weights'initialisation should also consider the Neuron's fan-in
        :return: the list of Neurons that compose the Neural Network
        '''
        units = []
        unit_type = ''
        unit_activation_function = ''
        unit_activation_function_args = []
        unit_successors = []
        unit_index = 0
        
        # All Neurons are initialised without synapses (successors/predecessors dependencies)
        for node in topology:
            unit_index = int(node)
            unit_type = topology[node][0]
            unit_activation_function = topology[node][1]
            unit_activation_function_args = [float(a) for a in topology[node][2]]
            
            if unit_type == 'input':
                self.input_size += 1
                units.append(InputNeuron(unit_index))
                
            elif unit_type == 'hidden':
                units.append(HiddenNeuron(unit_index, rand_range_min, rand_range_max, fan_in, self.__get_function_from_string(unit_activation_function), unit_activation_function_args))
                
            elif unit_type == 'output': # Fan-in is fixed as False for output units so to prevent Delta (Backpropagation Error Signal) to be a low value 
                self.output_size += 1
                units.append(OutputNeuron(unit_index, rand_range_min, rand_range_max, False, self.__get_function_from_string(unit_activation_function), unit_activation_function_args))
            
        # All Neurons' dependecies of successors and predecessors are filled inside the objects
        for node in topology:
            unit_type = topology[node][0]
            
            if unit_type != 'output': # Output units have no successors
                unit_successors = [units[int(u)] for u in topology[node][3]]
                units[int(node)].extend_successors(unit_successors)
        
        # All Neurons weights vectors are initialised
        for neuron in units:
            if neuron.type != 'input':
                neuron.initialise_weights(rand_range_min, rand_range_max, fan_in)

        return units
    
    def __topological_sort_util(self, index:int, visited:list, ordered:list):
        '''
        Recursive function that builds the topological(inverse) order updating ordered list 
        
        :param: index: the index of the neuron to visit
        :param: visited: the list of visited neurons
        :param: ordered: the list of ordered neurons (inverse topological order)
        :return: -
        '''
        visited[index] = True
        
        if self.neurons[index].type != 'output':
            for succ in self.neurons[index].successors:
                if not visited[succ.index]:
                    self.__topological_sort_util(succ.index, visited, ordered)
        
        ordered.append(self.neurons[index])
    
    def __topological_sort(self):
        '''
        Sort on a topological order the neurons of the Neural Network
        
        :param: -
        :return: -
        '''

        visited = [False]*self.n_neurons
        ordered = []
        
        for i in range(self.n_neurons):
            if not visited[i]:
                self.__topological_sort_util(i, visited, ordered)
        
        self.neurons = ordered[::-1]
                
    def __init__(self, topology:dict = {}, rand_range_min:float = -1, rand_range_max:float = 1, fan_in:bool = True):
        '''
        Neural Network inizialization
        
        :param topology: the graph structure is described by a dictionary that has a key for each unit in the network, 
            and for each key contains a list of unit type (input, hidden, output), activation function, parameters of activation functions
            and list of nodes where an outgoing arc terminates.
            
            eg: {'0': ['input', 'None', [], ['2', '3', '4']], 
                 '1': ['input', 'None', [], ['2', '3', '4']],
                 '2': ['hidden', 'sigmoid', [fun_args...], ['5', '6']],
                 '3': ['hidden', 'sigmoid', [fun_args...], ['5', '6']],
                 '4': ['hidden', 'sigmoid', [fun_args...], ['5', '6']],
                 '5': ['output', 'identity', [fun_args...], []],
                 '6': ['output', 'identity', [fun_args...], []]}

        :param: rand_range_min: minimum value for random weights initialisation range
        :param: rand_range_max: maximum value for random weights initialisation range
        :param: fan_in: if the weights'initialisation should also consider the Neuron's fan-in
        :return: -
        '''

        self.input_size = 0
        self.output_size = 0
        self.neurons = self.__construct_from_dict(topology, rand_range_min, rand_range_max, fan_in)
        self.n_neurons = len(self.neurons)
        self.__topological_sort() # The NN keeps its neurons in topological order
    
    def __str__(self):
        '''
        Return a string that describe the internal state of the neural network
        
        :return: the description of the internal rapresentation
        '''
        attributes = ", ".join(f"{attr}={getattr(self, attr)}" for attr in vars(self))
        return f"{self.__class__.__name__}({attributes})"
    
    def predict(self, input:numpy.array):
        '''
        Compute the output of the network given an input vector
        
        :param input: the input vector for the model
        :return: the network's output vector
        '''
        output_vector = numpy.zeros(self.output_size)
        
        # The input is forwarded towards the input units
        feature_index = 0
        for neuron in self.neurons[0:self.input_size]:
            neuron.forward(input[feature_index])
            feature_index += 1
        
        # The hidden units will now take their predecessors results forwarding the signal throught the network
        for neuron in self.neurons[self.input_size:self.n_neurons-self.output_size]:
            neuron.forward()
            
        # The output units will now take their predecessors results producing (returning) teh network's output
        feature_index = 0
        for neuron in self.neurons[self.n_neurons-self.output_size:]:
            output_vector[feature_index] = neuron.forward()
            feature_index += 1
            
        return output_vector
          
    def __backpropagation(self, target:numpy.array):
        '''
        Compute the Backpropagation training algorithm on the NN for a single training pattern
        
        :param target: the target vector for the Backprogation iteration
        :return: -
        '''
        nn_neuron_index = self.n_neurons -1
        
        # The error is calculated in the ouput units and propagated backwards
        target_index = len(target) - 1
        while nn_neuron_index >= self.n_neurons-self.output_size:
            self.neurons[nn_neuron_index].backward(target[target_index])
            target_index -= 1
            nn_neuron_index -= 1
        
        # The hidden units will now calculate their errors based on the signal propagated by their successors in the nn
        while nn_neuron_index >= self.input_size:
            self.neurons[nn_neuron_index].backward()
            nn_neuron_index -= 1
    
    def __mean_euclidean_error(self, outputs:numpy.ndarray, targets:numpy.ndarray):
        return (numpy.sum(numpy.linalg.norm(outputs-targets, axis = 1)))/len(outputs)
    
    def train(self, training_set:numpy.ndarray, minibatch_size:int, max_epochs:int, error_function:str, error_decrease_tolerance:float, patience: int, learning_rate:float = 1, lambda_tikhonov:float = 0.0, alpha_momentum:float = 0.0, nesterov_momentum:bool = False):
        '''
        Compute the Backpropagation training algorithm on the NN for given training samples and hyperparameters
        
        :param training_set: a set of samples (pattern-target pairs) for supervised learning
        :param minibatch_size: parameter which determines the amount of training samples consumed in each iteration of the algorithm
            -> 1: Online
            -> 1 < minibatch_size < len(TR): Minibatch with minibatch size equals to minibatch_size
            -> len(TR): Batch
        :param max_epochs: the maximum number of epochs (consumption of the whole training set) on which the algorithm will iterate
        :param error_function: a string indicating the error function that the algorithm whould exploit when calculating the error distances between iterations
            -> "mee": Mean Euclidean Error
            -> "lms": Least Mean Square
        :param error_decrease_tolerance: the errors difference (gain) value that the algorithm should consider as sufficiently low in order to stop training 
        :param patience: the number of epochs to wait when a "no more significant error decrease" occurs
        :param learning_rate: Eta hyperparameter to control the learning rate of the algorithm
        :param lambda_tikhonov: Lambda hyperparameter to control the learning algorithm complexity (Tikhonov Regularization / Ridge Regression)
        :param alpha_momentum: Momentum Hyperparameter
        :param nesterov_momentum: if the current training algorithm should exploit Nesterov's Momentum formulation
        :return: -
        '''
        #TODO Controllare i valori e capire se sono permessi (ad esempio minibatch_size > 0 ecc...)
        
        epochs = 0
        exhausting_patience = patience
        last_error_decrease_percentage = 1
        last_error = 0
        new_error = 0
        last_sample_index = 0
        training_set_length = len(training_set)
        minibatch = []
        minibatch_targets = numpy.ndarray((minibatch_size, self.output_size))
        minibatch_outputs = numpy.ndarray((minibatch_size, self.output_size))
        i = 0
        
        while epochs <= max_epochs and (last_error_decrease_percentage > error_decrease_tolerance or exhausting_patience > 0):
            if last_error_decrease_percentage <= error_decrease_tolerance:
                exhausting_patience -= 1
            else:
                exhausting_patience = patience
                
            if (last_sample_index + minibatch_size) > training_set_length:
                epochs += 1
                minibatch.extend(training_set[last_sample_index + 1:])
                minibatch.extend(training_set[0:minibatch_size - (training_set_length - last_sample_index)])
                last_sample_index = minibatch_size - (training_set_length - last_sample_index)
            else:
                minibatch.extend(training_set[last_sample_index + 1: (last_sample_index + minibatch_size)])
                last_sample_index = (last_sample_index + minibatch_size)
                
            i = 0    
            for sample in minibatch:
                minibatch_outputs[i] = self.predict(sample[0:self.input_size])
                minibatch_targets[i] = sample[self.input_size:]
                self.__backpropagation(sample[self.input_size + 1:])
                i += 1
               
            for neuron in self.neurons[self.input_size:]:
                neuron.update_weights(learning_rate, lambda_tikhonov, alpha_momentum, nesterov_momentum)
                
            if error_function == "mee":
                new_error = self.__mean_euclidean_error(minibatch_outputs, minibatch_targets)
                
            last_error_decrease_percentage = abs(last_error - new_error)/last_error
            last_error = new_error
                
                
                
            
            
            
            
            

    


if __name__ == '__main__':
    topology = {'0': ['input', 'None', [], ['2', '3', '4', '5']], 
                '1': ['input', 'None', [], ['2', '3', '4', '6']],
                '2': ['hidden', 'identity', [], ['5', '6', '4']],
                '3': ['hidden', 'identity', [], ['5', '6']],
                '4': ['hidden', 'identity', [], ['5', '6']],
                '5': ['output', 'identity', [], []],
                '6': ['output', 'identity', [], []],
                '7': ['input', 'None', [], ['4', '6']]}
    
    nn = NeuralNetwork(topology, 7, 7, False)
        
    mb = numpy.array([[3,2,10], [3,2,10], [3,2,10], [3,2,10], [3,2,10], [3,2,10]])
    #print(nn.forward(mb))
    
    for neuron in nn.neurons:
        print(neuron.output_list)