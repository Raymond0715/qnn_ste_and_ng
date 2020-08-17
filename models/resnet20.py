import tensorflow as tf
from tensorflow.keras.layers import Dense, Activation, Flatten
from tensorflow.keras.layers import Conv2D, MaxPooling2D, BatchNormalization
from tensorflow.keras import regularizers

from nn_utils import QConv2D
from quantization import QuantilizeFn 

import pdb

BITW = 4
BITA = 4
QuantilizeWeight, QuantilizeActivation = QuantilizeFn(BITW, BITA)


class ResnetUnitL2(tf.keras.layers.Layer):
    def __init__(
            self, 
            outputs_depth, 
            strides = 1, 
            first = False, 
            quantization = False,
            weight_decay = 0.0005):

        super(ResnetUnitL2, self).__init__()
        self.strides = strides
        self.first = first
        self.quantization = quantization

        self.conv2a = QConv2D(
                outputs_depth, 3, strides, quantilize = self.quantization, 
                weight_decay = weight_decay, use_bias = False)
            
        self.bn2a = BatchNormalization()
        
        self.conv2b = QConv2D(
                outputs_depth, 3, quantilize = self.quantization,
                weight_decay = weight_decay, use_bias = False)

        self.bn2b = BatchNormalization()

        if self.first:
            self.conv_shortcut = QConv2D(
                    outputs_depth, 1, strides, quantilize = self.quantization, 
                    weight_decay = weight_decay, use_bias = False)
            self.bn_shortcut = BatchNormalization()

    def call(self, input_tensor):
        x = input_tensor
        if self.first:
            shortcut = self.conv_shortcut(x)
            shortcut = self.bn_shortcut(shortcut)
        else:
            shortcut = x

        x = self.conv2a(x)
        x = self.bn2a(x)
        x = Activation('relu')(x)

        x = self.conv2b(x)
        x = self.bn2b(x)

        x += shortcut
        x = Activation('relu')(x)
        return x


class ResnetBlockL2(tf.keras.layers.Layer):
    def __init__(
            self,
            num_units,
            outputs_depth,
            strides,
            quantization = False,
            weight_decay = 0.0005):

        super(ResnetBlockL2, self).__init__()
        self.num_units = num_units
        self.units = []
        self.units.append(
                ResnetUnitL2(
                    outputs_depth, strides = strides, first = True, 
                    quantization = quantization, weight_decay = weight_decay))
        for i in range(1, self.num_units):
            self.units.append(
                    ResnetUnitL2( 
                        outputs_depth, quantization = quantization, 
                        weight_decay = weight_decay))

    def call(self, input_tensor):
        x = input_tensor
        for i in range(self.num_units):
            x = self.units[i](x)

        return x


class Resnet20(tf.keras.Model):
    def __init__(
            self,
            weight_decay,
            class_num,
            quantization = False):

        super(Resnet20, self).__init__(name = '')
        self.quantization = quantization

        self.conv_first = QConv2D(
                # 16, 3, quantilize = self.quantization, 
                16, 3, quantilize = False, 
                weight_decay = weight_decay, use_bias = False)
        self.bn_first = BatchNormalization()
        self.dense = Dense(
                class_num, 
                kernel_regularizer = regularizers.l2(weight_decay))
        self.block1 = ResnetBlockL2(
                3, 16, 1, 
                quantization = quantization, weight_decay = weight_decay)
        self.block2 = ResnetBlockL2(
                3, 32, 2, 
                quantization = quantization, weight_decay = weight_decay)
        self.block3 = ResnetBlockL2(
                3, 64, 2, 
                quantization = quantization, weight_decay = weight_decay)

    def call(self, input_tensor):
        x = input_tensor
        x = self.conv_first(x)
        x = self.bn_first(x)
        x = Activation('relu')(x)

        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)

        x = MaxPooling2D(pool_size = 8)(x)
        x = Flatten()(x)
        x = self.dense(x)

        return Activation('softmax')(x)

# weight_decay = 0.0005
# quantization = False
weight_decay = 0.0005
quantization = True
class_num = 10

model = Resnet20(weight_decay, class_num, quantization = quantization)


# inputs = tf.keras.Input(shape=(32,32,3))
# x = Conv2D(
        # 16, 3, padding = 'same', use_bias = False, 
        # kernel_regularizer = regularizers.l2(weight_decay))(inputs)
# x = BatchNormalization()(x)
# x = Activation('relu')(x)

# # Block 1, channels: 16
# # Block 1, unit 1
# shortcut = Conv2D(
        # 16, 1, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# shortcut = BatchNormalization()(shortcut)

# x = Conv2D(
        # 16, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x = Activation('relu')(x)
# x = Conv2D(
        # 16, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x += shortcut
# x = Activation('relu')(x)

# # Block 1, unit 2
# shortcut = x

# x = Conv2D(
        # 16, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x = Activation('relu')(x)
# x = Conv2D(
        # 16, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x += shortcut
# x = Activation('relu')(x)

# # Block 1, unit 3
# shortcut = x

# x = Conv2D(
        # 16, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x = Activation('relu')(x)
# x = Conv2D(
        # 16, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x += shortcut
# x = Activation('relu')(x)


# # Block 2, channels: 32
# # Block 2, unit 1
# shortcut = Conv2D(
        # 32, 1, strides = 2, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# shortcut = BatchNormalization()(shortcut)

# x = Conv2D(
        # 32, 3, strides = 2, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x = Activation('relu')(x)
# x = Conv2D(
        # 32, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x += shortcut
# x = Activation('relu')(x)

# # Block 2, unit 2
# shortcut = x

# x = Conv2D(
        # 32, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x = Activation('relu')(x)
# x = Conv2D(
        # 32, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x += shortcut
# x = Activation('relu')(x)

# # Block 2, unit 3
# shortcut = x

# x = Conv2D(
        # 32, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x = Activation('relu')(x)
# x = Conv2D(
        # 32, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x += shortcut
# x = Activation('relu')(x)

# # Block 3, channels: 64
# # Block 3, unit 1
# shortcut = Conv2D(
        # 64, 1, strides = 2, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# shortcut = BatchNormalization()(shortcut)

# x = Conv2D(
        # 64, 3, strides = 2, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x = Activation('relu')(x)
# x = Conv2D(
        # 64, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x += shortcut
# x = Activation('relu')(x)

# # Block 3, unit 2
# shortcut = x

# x = Conv2D(
        # 64, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x = Activation('relu')(x)
# x = Conv2D(
        # 64, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x += shortcut
# x = Activation('relu')(x)

# # Block 3, unit 3
# shortcut = x

# x = Conv2D(
        # 64, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x = Activation('relu')(x)
# x = Conv2D(
        # 64, 3, padding = 'same', use_bias = False,
        # kernel_regularizer = regularizers.l2(weight_decay))(x)
# x = BatchNormalization()(x)
# x += shortcut
# x = Activation('relu')(x)

# x = MaxPooling2D(pool_size = 8)(x)
# x = Flatten()(x)
# x = Dense(10, kernel_regularizer = regularizers.l2(weight_decay))(x)
# outputs = Activation('softmax')(x)

# model = Model(inputs = inputs, outputs = outputs)
