import numpy
from ActivationFunctions import ActivationFunctions

from ABCNeuron import ABCNeuron

class HiddenNeuron(ABCNeuron):
    '''
    Implementation of an hidden neuron composing the NN
    
    Attributes
    ----------
    index : int
        the index of the neuron in the NN
    type : str
        the type of the neuron
    predecessors : list of neurons
        list of neurons sending their outputs in input to this neuron
    n_predecessors: int
        number of units linked as predecessors to this neuron
    successors : list of neurons
        list of neurons receiving this neuron's outputs
    n_successors: int
        number of units linked as successors to this neuron
    w : array of float
        weights vector
    f : callable
        activation function
    f_parameters : list of float
        the list for the additional (optional) parameters of the activation function
    net : float
        inner product between the weight vector and the unit's input at a given iteration
    last_predict : float
        output of the neuron (instance variable exploited for predictions out of training)
    delta_error : float
        the last error signal related to the unit's output
    partial_weight_update : array of float
        the partial sum (on the minibatch) that will compose the DeltaW weight update value
    old_weight_update : array of float
        the old weight update value DeltaW
    partial_successors_weighted_errors : float
        the partial sum of successors' errors values weighted by the weight of the link bethween the two units

    '''

    def __init__(self, index:int, rand_range_min:float = -1, rand_range_max:float = 1, fan_in:bool = True, activation_fun:callable = ActivationFunctions.sigmoid,  *args):
        '''
        Neuron initialisation
        
        param index: the index of the neuron in the NN
        param n_input: the number of inputs receivable by the Neuron
        param activation_fun: the Neuron's actviation function
        param rand_range_min: minimum value for random weights initialisation range
        param rand_range_max: maximum value for random weights initialisation range
        param fan_in: if the weights'initialisation should also consider the Neuron's fan-in
        param args: additional (optional) parameters of the activation function

        :return: -
        '''
        self.index = index
        self.type = 'hidden'
        self.predecessors = [] # list of neurons sending their outputs in input to this neuron
        self.n_predecessors = 0
        self.successors = [] # list of neurons receiving this neuron's outputs
        self.n_successors = 0
        self.w = numpy.array([]) # weights vector (initialised later)
        self.f = activation_fun # activation function
        self.f_parameters = list(*args) # creates the list for the additional (optional) parameters of the activation function
        self.net = 0.0 # inner product between the weight vector and the unit's input at a given iteration
        
        self.last_predict = 0.0 # output of the neuron (instance variable exploited for predictions out of training)
        self.delta_error = 0.0 # the error signal calculated in the backpropagation
        self.partial_weight_update = numpy.array([]) # the partial sum (on the minibatch) that will compose the DeltaW weight update value
        self.old_weight_update = numpy.array([]) # the old weight update value DeltaW
        self.partial_successors_weighted_errors = 0.0 # the partial sum of successors' errors values weighted by the weight of the link bethween the two units
        # the creation of the variable is not necessary because can be created in any moment, just having the istance of the object but
        # the None value can help in preventing error, also resetting the variable can help in this sense
    
    # TODO: farlo per bene per ora azzoppo tutto
    #def add_nesterov_momentum(self, alpha_momentum:float = 0.0):
        '''
        Updates the weight vector (w) of the Neuron with Nesterov's Momentum
        this update should be done before the next minibatch learning iteration
        
        :param alpha_momentum: Nertov's Momentum Hyperparameter
        :return: -
        '''
        
        #self.w = self.w + alpha_momentum*self.old_weight_update
    
    def update_weights(self, learning_rate:float = 1, lambda_tikhonov:float = 0.0, alpha_momentum:float = 0.0):
        '''
        Updates the weight vector (w) of the Neuron
        
        param learning_rate: Eta hyperparameter to control the learning rate of the algorithm
        param lambda_tikhonov: Lambda hyperparameter to control the learning algorithm complexity (Tikhonov Regularization / Ridge Regression)
        param alpha_momentum: Momentum Hyperparameter

        return: -
        '''

        # here we compute the weight update if the momentum is used or not
        weight_update = (learning_rate * self.partial_weight_update) + (alpha_momentum * self.old_weight_update)
        
        # the weight_update value is calculated separated from Tikhonov Regularization for code/concept cleanliness
        self.w += weight_update - (lambda_tikhonov * self.w)
        self.old_weight_update = weight_update

        
        
    def initialise_weights(self, rand_range_min:float, rand_range_max:float, fan_in:bool):
        '''
        Initialises the Neuron's weights vector (w).
        Updates the unit's numbers of predecessors and successors (the network has already been completely linked together)
        
        param rand_range_min: minimum value for random weights initialisation range
        param rand_range_max: maximum value for random weights initialisation range
        param fan_in: if the weights'initialisation should also consider the Neuron's fan-in

        return: -
        '''
        self.n_predecessors = len(self.predecessors)
        self.n_successors = len(self.successors)
        self.w = numpy.random.uniform(rand_range_min, rand_range_max, self.n_predecessors + 1) # the +1 is to count the bias
        self.old_weight_update = numpy.zeros(self.n_predecessors + 1) # bias
        self.partial_weight_update = numpy.zeros(self.n_predecessors + 1) # bias
        if fan_in:
            self.w = self.w * 2/(self.n_predecessors + 1) # TODO magari va tolto il +1 perchè il bias non è da contare
        
    def forward(self):
        '''
        Calculates the Neuron's output on the inputs incoming from the other units
        
        param input: Neuron's input vector

        return: -
        '''
        input = numpy.zeros(self.n_predecessors)
        input[0] = 1 #bias
        for index, p in enumerate(self.predecessors):
            input[index + 1] = p.last_predict

        self.net = numpy.inner(self.w, input)
        self.last_predict = self.f(self.net, *self.f_parameters)
     
    def accumulate_weighted_error(self, delta: float, weight: float):
        '''
        function used by successors, accumulate the weighted error of the successors

        param delta: the error of the successor
        param weight: the weight of the successor that correspond to the output of this unit

        return: -
        '''

        # summation
        self.partial_successors_weighted_errors += (delta * weight)
        
    def backward(self):
        '''
        Calculates the Neuron's error contribute for a given learning pattern
        Calculates a partial weight update for the Neuron (Partial Backpropagation)
        
        return: -
        '''
        
        predecessors_outputs = numpy.zeros(self.n_predecessors + 1) # bias
        
        # computing delta error of the unit (before we have accumulated the successor's deltas in 'partial_successors_weighted_errors')
        self.delta_error = self.partial_successors_weighted_errors * ActivationFunctions.derivative(self.f, self.net, *self.f_parameters)
        
        predecessors_outputs[0] = 1 # bias
        for index, p in enumerate(self.predecessors):
            predecessors_outputs[index + 1] = p.last_predict # bias
            #print("Predecessors output: ", p.last_predict)
            if p.type != "input":
                p.accumulate_weighted_error(self.delta_error, self.w[index + 1])# bias
            index += 1
        
        #print("INDEX: ", self.index, " ", "TYPE: ", self.type)
        #print("DELTA ERROR: ", self.delta_error)
        self.partial_weight_update += + (self.delta_error * predecessors_outputs)# accumulating weight updates for the batch version

    def add_successor(self, neuron):
        '''
        Adds a neuron to the list of the Neuron's successors and
        update the predecessors' list of the successor neuron with the current neuron
        
        param neuron: the Neuron to add to the list of successors

        return: -
        '''
        self.successors.append(neuron)
        neuron.add_predecessor(self)
    
    def extend_successors(self, neurons:list):
        '''
        Extends the list of the Neuron's successors and
        update the predecessors' list of the successors neurons with the current neuron
        
        param neurons: the list of Neurons to add to the list of successors

        return: -
        '''
        self.successors.extend(neurons)
        for successor in neurons:
            successor.add_predecessor(self)


    # TODO: sta funzione se viene usata credo crei problemi con un utilizzo contemporaneo anche della precedente, per ora la togliamo, se serve vebremo
    # TODO: eliminare?
    #def extend_predecessors(self, neurons:list):
        '''
        Extends the list of the Neuron's predecessors
        
        :param neurons: the list of Neurons to add to the list of predecessors
        :return: -
        '''
        #self.predecessors.extend(neurons)

    def add_predecessor(self, neuron):
        '''
        Adds a neuron to the list of the Neuron's predecessors
        
        param neuron: the Neuron to add to the list of predecessors

        return: -
        '''
        self.predecessors.append(neuron)
