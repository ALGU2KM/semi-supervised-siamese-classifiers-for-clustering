from __future__ import absolute_import
from __future__ import print_function
import numpy as np

import random
from sklearn.metrics import balanced_accuracy_score

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.datasets import mnist, fashion_mnist
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Flatten, Dense, Dropout, Lambda
from tensorflow.keras.optimizers import RMSprop
from tensorflow.keras import backend as K
from tensorflow.keras import losses
import tensorflow as tf
from tensorflow.keras.backend import set_session
from tensorflow.keras.utils import to_categorical
from tensorflow.keras import models, regularizers

from sklearn.metrics.cluster import adjusted_rand_score
from sklearn.metrics import v_measure_score
import argparse



pairs = np.array([100, 200, 500, 1000, 2000, 5000])
# pairs = np.array([1000])

labels_file = "labels"
pairs_file = "pairs"


margin = 1.
# siamese_threshold = .3

def euclidean_distance(vects):
    x, y = vects
    sum_square = K.sum(K.square(x - y), axis=1, keepdims=True)
    return K.sqrt(K.maximum(sum_square, K.epsilon()))


def eucl_dist_output_shape(shapes):
    shape1, shape2 = shapes
    return (shape1[0], 1)


def contrastive_loss(y_true, y_pred):
    '''Contrastive loss from Hadsell-et-al.'06
    http://yann.lecun.com/exdb/publis/pdf/hadsell-chopra-lecun-06.pdf
    '''
    sqaure_pred = K.square(y_pred)
    margin_square = K.square(K.maximum(margin - y_pred, 0))
    return K.mean(y_true * sqaure_pred + (1 - y_true) * margin_square)





def create_pairs(x, digit_indices, num_links_per_class, num_classes):
    '''Positive and negative pair creation.
    Alternates between positive and negative pairs.
    '''
    pairs = []
    labels = []
    n = min(min([len(digit_indices[d]) for d in range(num_classes)]) - 1, num_links_per_class)
    for d in range(num_classes):
        for i in range(n):
            z1, z2 = digit_indices[d][i], digit_indices[d][i + 1]
            pairs += [[x[z1], x[z2]]]
            inc = random.randrange(1, num_classes)
            dn = (d + inc) % num_classes
            z1, z2 = digit_indices[d][i], digit_indices[dn][i]
            pairs += [[x[z1], x[z2]]]
            labels += [1, 0]
    return np.array(pairs), np.array(labels)


def create_pairs_new(x, digit_indices, num_links):
    '''Positive and negative pair creation.
    Alternates between positive and negative pairs.
    '''
    pairs = []
    labels = []
    num_links_per_class = int(num_links/(2*num_classes))
    n = min( min([len(digit_indices[d]) for d in range(num_classes)]) - 1, num_links_per_class)
    for d in range(num_classes):
        for i in range(n):
            z1, z2 = digit_indices[d][i], digit_indices[d][i + 1]
            pairs += [[x[z1], x[z2]]]
            inc = random.randrange(1, num_classes)
            dn = (d + inc) % num_classes
            z1, z2 = digit_indices[d][i], digit_indices[dn][i]
            pairs += [[x[z1], x[z2]]]
            labels += [1, 0]
    return np.array(pairs), np.array(labels)

def generate_links(data, labels):
    idx = np.arange(0, len(data))
    np.random.shuffle(idx)
    num = int(len(data) / 2)
    idx1 = idx[:num]
    idx2 = idx[num:2 * num]
    links_data = [(data[idx1[i]], data[idx2[i]]) for i in np.arange(0, num)]
    links_labels = [1 if labels[idx1[i]] == labels[idx2[i]] else 0 for i in np.arange(0, num)]

    return np.asarray(links_data), np.asarray(links_labels)



def generate_pairs(data, labels, num):
    idx = np.arange(0, len(data))
    np.random.shuffle(idx)
    idx1 = idx[:num]
    idx2 = idx[num:2 * num]
    links_data = [(data[idx1[i]], data[idx2[i]]) for i in np.arange(0, num)]
    links_labels = [1 if labels[idx1[i]] == labels[idx2[i]] else 0 for i in np.arange(0, num)]

    return np.asarray(links_data), np.asarray(links_labels)



def shuffle_data(data, labels):
    idx = np.arange(0, len(data))
    np.random.shuffle(idx)
    sh_data = [data[idx[i]] for i in np.arange(0, len(data))]
    sh_labels = [labels[idx[i]] for i in np.arange(0, len(data))]

    return np.asarray(sh_data), np.asarray(sh_labels)


# def create_base_network(input_shape):
#     '''Base network to be shared (eq. to feature extraction).
#     '''
#     input = Input(shape=input_shape)
#     #     x = Flatten()(input)
#     x = Dense(128, activation='relu')(input)
#     x = Dropout(0.3)(x)
#     x = Dense(128, activation='relu')(x)
#     x = Dropout(0.3)(x)
#     x = Dense(128, activation='sigmoid')(x)
#     return Model(input, x)


def create_base_network_letters(input_shape):
    '''Base network to be shared (eq. to feature extraction).
    '''
    input = Input(shape=input_shape)
    #     x = Flatten()(input)
    x = Dense(256, activation='relu')(input)
    x = Dropout(0.1)(x)
    x = Dense(256, activation='relu')(x)
    x = Dropout(0.1)(x)
    x = Dense(256, activation='sigmoid')(x)
    return Model(input, x)

def create_base_network_mnist(input_shape):
    '''Base network to be shared (eq. to feature extraction).
    '''
    input = Input(shape=input_shape)
    #     x = Flatten()(input)
    x = Dense(256, activation='relu')(input)
    x = Dropout(0.1)(x)
    x = Dense(256, activation='relu')(x)
    x = Dropout(0.1)(x)
    x = Dense(256, activation='sigmoid')(x)
    return Model(input, x)

def create_base_network_reuters(input_shape):
    '''Base network to be shared (eq. to feature extraction).
    '''
    input = Input(shape=input_shape)
    #     x = Flatten()(input)
    x = Dense(256, kernel_regularizer=regularizers.l1(0.001), activation='relu')(input)
    x = Dropout(0.5)(x)
    x = Dense(256, kernel_regularizer=regularizers.l1(0.001), activation='relu')(x)
    x = Dropout(0.5)(x)
    x = Dense(256, activation='softmax')(x)
    return Model(input, x)


def compute_accuracy(y_true, y_pred):
    '''Compute classification accuracy with a fixed threshold on distances.
    '''
    pred = y_pred.ravel() < siamese_threshold
    return np.mean(pred == y_true)


def accuracy(y_true, y_pred):
    '''Compute classification accuracy with a fixed threshold on distances.
    '''
    return K.mean(K.equal(y_true, K.cast(y_pred < siamese_threshold, y_true.dtype)))


def accuracy_ml(y_true, y_pred):
    '''Compute classification accuracy with a fixed threshold on distances.
    '''
    return K.sum(y_true * K.cast(y_pred < siamese_threshold, y_true.dtype)) * 1. / K.sum(y_true)

def compute_accuracy_ml(y_true, y_pred):
    '''Compute classification accuracy with a fixed threshold on distances.
    '''
    pred = y_pred.ravel() < siamese_threshold
    return np.sum(y_true*pred) * 1./np.sum(y_true)

def accuracy_cl(y_true, y_pred):
    '''Compute classification accuracy with a fixed threshold on distances.
    '''
    return K.sum((1-y_true) * K.cast(y_pred > siamese_threshold, y_true.dtype)) * 1. / K.sum((1 - y_true))


def compute_accuracy_cl(y_true, y_pred):
    '''Compute classification accuracy with a fixed threshold on distances.
    '''
    pred = y_pred.ravel() > siamese_threshold
    return np.sum((1-y_true) * pred) * 1./np.sum((1-y_true))

def compute_balance_accuracy(y_true, y_pred):
    pred = y_pred.ravel() < siamese_threshold
    pred_int = pred.astype(int)
    return balanced_accuracy_score(y_true, pred_int)


def balance_accuracy(y_true, y_pred, num_classes):
    '''Compute classification accuracy with a fixed threshold on distances.
    '''
    pred = K.cast(y_pred < 0.5, y_true.dtype)
    return tf.metrics.mean_per_class_accuracy(y_true, pred, num_classes)


def generate_batch_dist(num, data, labels, knns):
    idx1 = np.arange(0, len(data))
    np.random.shuffle(idx1)
    idx2 = np.arange(0, len(data))
    np.random.shuffle(idx2)
    links_data = [(data[idx1[i]], data[idx2[i]]) for i in np.arange(0, num)]

    a = np.asarray(links_data)[:, 0, :]
    b = np.asarray(links_data)[:, 1, :]
    dist = np.linalg.norm(a - b, axis=1)
    inds = np.argpartition(dist, knns)
    links_pred = np.zeros(num)
    links_pred[inds[:knns]] = 1

    return np.asarray(links_data), links_pred  # np.squeeze(np.asarray(links_labels))


def generate_batch_unlinked_pei(num, data):
    idx1 = np.arange(0 , len(data))
    np.random.shuffle(idx1)
    idx2 = np.arange(0 , len(data))
    np.random.shuffle(idx2)
    links_data = [(data[idx1[i]], data[idx2[i]]) for i in np.arange(0,num)]
    return np.asarray(links_data)


def generate_batch_unlinked(num, data, labels, ml_threshold=0.5):
    idx1 = np.arange(0 , len(data))
    np.random.shuffle(idx1)
    idx2 = np.arange(0 , len(data))
    np.random.shuffle(idx2)
    links_data = [(data[idx1[i]], data[idx2[i]]) for i in np.arange(0,num)]
#     links_labels = [1 if labels[idx1[i]]==labels[idx2[i]] else 0 for i in np.arange(0,num)]
    links_pred = model.predict([data[idx1[:num]], data[idx2[:num]]])
    links_labels = (links_pred.ravel() < ml_threshold).astype(float)
    return np.asarray(links_data), np.squeeze(np.asarray(links_labels))


def generate_batch_links(num, data_pairs, labels):
    idx = np.arange(0, len(data_pairs))
    np.random.shuffle(idx)
    return data_pairs[idx[:num]], labels[idx[:num]]


def my_loss(y_pred, must_true_probs):
    size = tf.shape(must_true_probs)[0]
    res_mul = tf.reduce_sum(tf.multiply(y_pred[:size,:], y_pred[size:,:]), axis=1)
    weight_true = 2*must_true_probs - 1
    res = tf.multiply(weight_true, tf.squeeze(res_mul))
    return -tf.reduce_mean(res)


def my_loss_plus_self(y_pred, must_true_probs):
    size = tf.shape(must_true_probs)[0]

    self_mul = tf.reduce_sum(tf.multiply(y_pred[:2 * size, :], y_pred[:2 * size, :]), axis=1)

    res_mul = tf.reduce_sum(tf.multiply(y_pred[:size, :], y_pred[size:, :]), axis=1)
    weight_true = 2 * must_true_probs - 1
    res = tf.multiply(weight_true, tf.squeeze(res_mul))
    return -tf.reduce_mean(res) - tf.reduce_mean(self_mul)


def pei_loss(y_pred, must_true_probs):
    y_pred = tf.clip_by_value(y_pred, 1e-3, 1.0 - 1e-3)
    size = tf.shape(must_true_probs)[0]
    # linki
    res_mul = tf.reduce_sum(tf.multiply(y_pred[:size, :], y_pred[size:2 * size, :]), axis=1)
    weight_true = 2 * must_true_probs - 1
    weight_2 = 1 - must_true_probs
    inner_res = weight_2 + tf.multiply(weight_true, tf.squeeze(res_mul))
    res_links = -tf.reduce_mean(tf.log(inner_res))

    # balans
    p_y = tf.reduce_mean(y_pred, axis=0)
    log_p_y = tf.log(p_y)
    entropy = -tf.reduce_sum(tf.multiply(p_y, log_p_y))
    # pewnosc
    log_y_pred = tf.log(y_pred)
    cond_entropy = tf.reduce_sum(tf.multiply(y_pred, log_y_pred), axis=1)
    sum_cond_entropy = -tf.reduce_mean(cond_entropy)
    # wzajemna inf
    mi = sum_cond_entropy - entropy

    return mi + res_links


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', default='mnist')  #"mnist"  # "fashion"
    parser.add_argument('--loss_mode', default='siamese_loss')   #"siamese_loss"  # pei_loss, dist_loss
    parser.add_argument('--learning_type', default='semi')    #"semi"  # supervised
    parser.add_argument('--siamese_epoch', default=100, type=int)
    parser.add_argument('--clustering_iterations', default=2000, type=int)
    parser.add_argument('--unlinked_batch', default=1000, type=int)
    parser.add_argument('--links_batch', default=100, type=int)
    parser.add_argument('--siamese_threshold', default=0.3, type=float)
    parser.add_argument('--knns', default=100, type=int)
    parser.add_argument('--lr_siamese', default=0.001, type=float)
    parser.add_argument('--lr_clustering', default=0.001, type=float)


    #
    args = parser.parse_args()
    #
    # #parameters
    dataset = args.dataset
    loss_mode = args.loss_mode
    learning_type = args.learning_type
    siamese_epoch = args.siamese_epoch
    clustering_iterations = args.clustering_iterations
    unlinked_batch = args.unlinked_batch
    links_batch = args.links_batch
    siamese_threshold = args.siamese_threshold
    knns = args.knns
    lr_siamese = args.lr_siamese
    lr_clustering = args.lr_clustering




    if dataset == "mnist":
        (x_train, y_train), (x_test, y_test) = mnist.load_data()
    elif dataset == "fashion":
        (x_train, y_train), (x_test, y_test) = fashion_mnist.load_data()
    elif dataset == "letters":
        x_train = np.load("dane/" + dataset + "/x_train.npy")
        y_train = np.load("dane/" + dataset + "/y_train.npy")
        y_train_save = np.load("dane/" + dataset + "/y_train_save.npy")
        x_test = np.load("dane/" + dataset + "/x_test.npy")
        y_test = np.load("dane/" + dataset + "/y_test.npy")
        y_test_save = np.load("dane/" + dataset + "/y_test_save.npy")
    elif dataset == "reuters":
        rtk10k_train = np.load("dane/" + dataset + "/reutersidf10k_train.npy").item()
        x_train = rtk10k_train['data']
        y_train = rtk10k_train['label']
        rtk10k_test = np.load("dane/" + dataset + "/reutersidf10k_test.npy").item()
        x_test = rtk10k_test['data']
        y_test = rtk10k_test['label']

        y_train_save = y_train
        y_test_save = y_test

        y_train = to_categorical(y_train)
        y_test = to_categorical(y_test)

    else:
        print("brak zestawu danych")

    if dataset == "mnist" or dataset == "fashion":
        x_train = x_train.astype('float32')
        x_test = x_test.astype('float32')
        x_train /= 255
        x_test /= 255

        y_train_save = y_train
        y_test_save = y_test

        # Flatten the images
        image_vector_size = 28 * 28
        x_train = x_train.reshape(x_train.shape[0], image_vector_size)
        x_test = x_test.reshape(x_test.shape[0], image_vector_size)
        y_train = np.eye(10)[y_train]
        y_test = np.eye(10)[y_test]

    input_shape = x_train.shape[1:]
    num_classes = len(np.unique(y_train_save))

    print("-------------PARAMS----------------------")
    print("dataset: ", dataset)
    print("loss_mode: ", loss_mode)
    print("learning_type: ", learning_type)
    print("siamese_epoch: ", str(siamese_epoch))
    print("clustering_iterations: ", str(clustering_iterations))
    print("unlinked_batch: ", str(unlinked_batch))
    print("links_batch: ", str(links_batch))
    print("siamese_threshold: ", str(siamese_threshold))
    print("knns: ", str(knns))
    print("lr_siamese: ", str(lr_siamese))
    print("lr_clustering: ", str(lr_clustering))

    for no_of_pairs in pairs:
        # for ver in range(1):
        for ver in range(5):

            # create training+test positive and negative pairs
            tr_y = np.load("dane/" + dataset + "/" + str(no_of_pairs) + "/" + labels_file + "-ver-" + str(ver) + ".npy")
            tr_pairs = np.load("dane/" + dataset + "/" + str(no_of_pairs) + "/" + pairs_file + "-ver-" + str(ver) + ".npy")
            # tr_pairs, tr_y = generate_pairs(x_train, y_train_save, no_of_pairs)
            # digit_indices = [np.where(y_train_save == i)[0] for i in range(num_classes)]
            # tr_pairs, tr_y = create_pairs_new(x_train, digit_indices, no_of_pairs)

            digit_indices = [np.where(y_test_save == i)[0] for i in range(num_classes)]
            te_pairs, te_y = create_pairs(x_test, digit_indices, 1000000, num_classes)

            te_pairs_u, te_y_u = generate_links(x_train, y_train_save)

            K.clear_session()
            tf.reset_default_graph()



            if loss_mode == "siamese_loss" and learning_type == "semi":
                # network definition
                if dataset == "reuters":
                    base_network = create_base_network_reuters(input_shape)
                elif dataset == "mnist" or dataset == "fashion":
                    base_network = create_base_network_mnist(input_shape)
                elif dataset == "letters":
                    base_network = create_base_network_letters(input_shape)
                else:
                    print("nie ma takiego zbioru")
                    # base_network = create_base_network(input_shape)

                input_a = Input(shape=input_shape)
                input_b = Input(shape=input_shape)
                processed_a = base_network(input_a)
                processed_b = base_network(input_b)
                distance = Lambda(euclidean_distance, output_shape=eucl_dist_output_shape)
                dist_output = distance([processed_a, processed_b])
                model = Model([input_a, input_b], dist_output)

                config_keras = tf.ConfigProto()
                config_keras.gpu_options.allow_growth = True
                sess_keras = tf.Session(config=config_keras)
                set_session(sess_keras)

                # train
                rms = RMSprop(lr=lr_siamese)
                model.compile(loss=contrastive_loss, optimizer=rms, metrics=[accuracy, accuracy_ml, accuracy_cl])
                if dataset == "mnist" or  dataset == "fashion":
                    model.fit([tr_pairs[:, 0], tr_pairs[:, 1]], tr_y,
                              batch_size=256,
                              epochs=siamese_epoch,
                              validation_data=([te_pairs[:, 0], te_pairs[:, 1]], te_y))
                elif dataset == "letters":
                    model.fit([tr_pairs[:, 0], tr_pairs[:, 1]], tr_y,
                              batch_size=128,
                              epochs=siamese_epoch,
                              validation_data=([te_pairs[:, 0], te_pairs[:, 1]], te_y))
                else:
                    model.fit([tr_pairs[:, 0], tr_pairs[:, 1]], tr_y,
                              batch_size=256,
                              epochs=siamese_epoch,
                              validation_data=([te_pairs[:, 0], te_pairs[:, 1]], te_y))

                model.save_weights("models/" + dataset + "/" + str(no_of_pairs) + "/model-" + loss_mode +
                                   "-" + learning_type + "-ver-" + str(ver) + "-u-" + str(unlinked_batch) +
                                   "-l-" + str(links_batch) + "-t-" + str(siamese_threshold) +
                                   "-k-" + str(knns) + "-lrs-" + str(lr_siamese) + "-lrc-" + str(lr_clustering) + ".h5")



                # compute final accuracy on training and test sets
                y_pred = model.predict([tr_pairs[:, 0], tr_pairs[:, 1]])
                tr_acc = compute_accuracy(tr_y, y_pred)
                y_pred = model.predict([te_pairs[:, 0], te_pairs[:, 1]])
                te_acc = compute_accuracy(te_y, y_pred)
                te_ml = compute_accuracy_ml(te_y, y_pred)
                te_cl = compute_accuracy_cl(te_y, y_pred)

                # y_pred_u = model.predict([te_pairs_u[:, 0], te_pairs_u[:, 1]])
                # te_acc_u = compute_balance_accuracy(te_y_u, y_pred_u)
                # y_pred_b = model.predict([te_pairs_u[:, 0], te_pairs_u[:, 1]])
                # te_acc_b = compute_accuracy(te_y_u, y_pred_u)
                print('* Accuracy on training set: %0.2f%%' % (100 * tr_acc))
                print('* Accuracy on test set: %0.2f%%' % (100 * te_acc))
                print('* ML Accuracy on test set: %0.2f%%' % (100 * te_ml))
                print('* CL Accuracy on test set: %0.2f%%' % (100 * te_cl))
                siamese_res = np.array([tr_acc, te_acc, te_ml, te_cl])
                np.savetxt("results/" + dataset + "/" + str(no_of_pairs) + "/siamese-" + loss_mode +
                           "-" + learning_type + "-ver-" + str(ver) + "-u-" + str(unlinked_batch) +
                           "-l-" + str(links_batch) + "-t-" + str(siamese_threshold) +
                           "-k-" + str(knns) + "-lrs-" + str(lr_siamese) + "-lrc-" + str(lr_clustering)  +
                           ".txt", siamese_res, fmt="%.5f")

            img = tf.placeholder(tf.float32, shape=(None, input_shape[0]))
            labels = tf.placeholder(tf.float32, shape=(None))

            # Keras layers can be called on TensorFlow tensors:
            if dataset == "reuters":
                x = Dense(256, activation='relu')(img)  # fully-connected layer with 128 units and ReLU activation
                x = Dropout(0.5)(x)
                x = Dense(256, activation='relu')(x)
                x = Dropout(0.5)(x)
                preds = Dense(num_classes, activation='softmax')(x)
            elif dataset == "mnist" or "fashion":
                x = Dense(256, activation='relu')(img)  # fully-connected layer with 128 units and ReLU activation
                x = Dropout(0.1)(x)
                x = Dense(256, activation='relu')(x)
                x = Dropout(0.1)(x)
                preds = Dense(num_classes, activation='softmax')(x)
            elif dataset == "letters":
                x = Dense(256, activation='relu')(img)  # fully-connected layer with 128 units and ReLU activation
                x = Dropout(0.1)(x)
                x = Dense(256, activation='relu')(x)
                x = Dropout(0.1)(x)
                preds = Dense(num_classes, activation='softmax')(x)
            else:
                # x = Dense(256, activation='relu')(img)  # fully-connected layer with 128 units and ReLU activation
                # x = Dropout(0.1)(x)
                # x = Dense(256, activation='relu')(x)
                # x = Dropout(0.1)(x)
                # preds = Dense(num_classes, activation='softmax')(x)
                print("error - no data")


            if loss_mode == "siamese_loss" or loss_mode == "dist_loss":
                lo = my_loss(preds, labels)
            elif loss_mode == "pei_loss":
                lo = pei_loss(preds, labels)
            else:
                print("ERROR: nie zaimplementowano loss")

            train_step = tf.train.AdamOptimizer(lr_clustering).minimize(lo)

            ari_list = np.array([])
            nmi_list = np.array([])

            # val_summary = tf.placeholder(tf.float32, shape=())
            # loss_summary = tf.summary.scalar('loss_train', lo)
            # nmi_summary = tf.summary.scalar('nmi', val_summary)
            # ari_summary = tf.summary.scalar('ari', val_summary)
            # train_writer = tf.summary.FileWriter("results/" + dataset + "/" + str(no_of_pairs) + "/summary-" + loss_mode +
            #                "-" + learning_type + "-ver-" + str(ver) + "-u-" + str(unlinked_batch) +
            #                "-l-" + str(links_batch) + "-t-" + str(siamese_threshold) +
            #                "-k-" + str(knns) + "-lrs-" + str(lr_siamese) + "-lrc-" + str(lr_clustering))

            config = tf.ConfigProto()
            config.gpu_options.allow_growth = True

            with tf.Session(config=config) as sess:
                sess.run(tf.global_variables_initializer())

                if loss_mode == "siamese_loss" and learning_type == "semi":
                    model.load_weights("models/" + dataset + "/" + str(no_of_pairs) + "/model-" + loss_mode +
                                       "-" + learning_type + "-ver-" + str(ver) + "-u-" + str(unlinked_batch) +
                                       "-l-" + str(links_batch) + "-t-" + str(siamese_threshold) +
                                       "-k-" + str(knns) + "-lrs-" + str(lr_siamese) + "-lrc-" + str(lr_clustering) + ".h5")

                for i in range(clustering_iterations):

                    if loss_mode == "siamese_loss" and learning_type == "semi":
                        batch1 = generate_batch_unlinked(unlinked_batch, x_train, y_train_save, siamese_threshold)
                        batch2 = generate_batch_links(links_batch, tr_pairs, tr_y)
                        batch_data = np.vstack((batch1[0], batch2[0]))
                        batch_labs = np.hstack((batch1[1], batch2[1]))
                        stacked_data = np.vstack((batch_data[:, 0, :], batch_data[:, 1, :]))
                        train_step.run(feed_dict={img: stacked_data, labels: batch_labs})
                        # loss_summ = sess.run(loss_summary,
                        #                     feed_dict={img: stacked_data, labels: batch_labs})
                        # train_writer.add_summary(loss_summ, i)
                    elif loss_mode == "pei_loss" and learning_type == "semi":
                        batch_unlinked = generate_batch_unlinked_pei(unlinked_batch, x_train)
                        batch_linked = generate_batch_links(links_batch, tr_pairs, tr_y)
                        batch_data = np.vstack((batch_linked[0][:, 0, :], batch_linked[0][:, 1, :],
                                                batch_unlinked[:, 0, :], batch_unlinked[:, 1, :]))
                        train_step.run(feed_dict={img: batch_data, labels: batch_linked[1]})
                        # loss_summ = sess.run(loss_summary,
                        #                      feed_dict={img: batch_data, labels:  batch_linked[1]})
                        # train_writer.add_summary(loss_summ, i)
                    elif loss_mode == "dist_loss" and learning_type == "semi":
                        batch1 = generate_batch_dist(unlinked_batch, x_train, y_train_save, knns)
                        batch2 = generate_batch_links(links_batch, tr_pairs, tr_y)
                        batch_data = np.vstack((batch1[0], batch2[0]))
                        batch_labs = np.hstack((batch1[1], batch2[1]))
                        stacked_data = np.vstack((batch_data[:, 0, :], batch_data[:, 1, :]))
                        train_step.run(feed_dict={img: stacked_data, labels: batch_labs})
                        # loss_summ = sess.run(loss_summary,
                        #                      feed_dict={img: stacked_data, labels: batch_labs})
                        # train_writer.add_summary(loss_summ, i)
                    elif learning_type == "supervised":
                        batch = generate_batch_links(links_batch, tr_pairs, tr_y)
                        stacked_data = np.vstack((batch[0][:,0,:], batch[0][:,1,:]))
                        train_step.run(feed_dict={img: stacked_data, labels: batch[1]})
                        # loss_summ = sess.run(loss_summary,
                        #                      feed_dict={img: stacked_data, labels: batch[1]})
                        # train_writer.add_summary(loss_summ, i)
                    else:
                        print("ERROR: nie ma takiego treningu")

                    # Print the validation accuracy every 100 steps
                    if i % 100 == 0:
                        pred_test = preds.eval(feed_dict={img: x_test})
                        yy = sess.run(tf.argmax(y_test, 1))
                        pp = sess.run(tf.argmax(pred_test, 1))
                        ari = adjusted_rand_score(yy, pp)
                        nmi = v_measure_score(yy, pp)
                        print('step: {}, validation ari: {}, nmi: {}'.format(i, round(ari, 3), round(nmi, 3)))
                        ari_list = np.append(ari_list, ari)
                        nmi_list = np.append(nmi_list, nmi)

                        # loss_summ = sess.run(nmi_summary, feed_dict={val_summary: nmi})
                        # train_writer.add_summary(loss_summ, i)
                        # loss_summ = sess.run(ari_summary, feed_dict={val_summary: ari})
                        # train_writer.add_summary(loss_summ, i)

                # train_writer.close()

                #summarize the results
                pred_test = preds.eval(feed_dict={img: x_test})
                yy = sess.run(tf.argmax(y_test, 1))
                pp = sess.run(tf.argmax(pred_test, 1))
                ari = adjusted_rand_score(yy, pp)
                nmi = v_measure_score(yy, pp)
                print('TEST ari: {}, nmi: {}'.format(round(ari, 3), round(nmi, 3)))
                ari_list = np.append(ari_list, ari)
                nmi_list = np.append(nmi_list, nmi)
                np.savetxt("results/" + dataset + "/" + str(no_of_pairs) + "/ari-" + loss_mode +
                           "-" + learning_type + "-ver-" + str(ver) + "-u-" + str(unlinked_batch) +
                           "-l-" + str(links_batch) + "-t-" + str(siamese_threshold) +
                           "-k-" + str(knns) + "-lrs-" + str(lr_siamese) + "-lrc-" + str(lr_clustering)
                           + ".txt", ari_list, fmt="%.5f")
                np.savetxt("results/" + dataset + "/" + str(no_of_pairs) + "/nmi-" + loss_mode +
                           "-" + learning_type + "-ver-" + str(ver) + "-u-" + str(unlinked_batch) +
                           "-l-" + str(links_batch) + "-t-" + str(siamese_threshold) +
                           "-k-" + str(knns) + "-lrs-" + str(lr_siamese) + "-lrc-" + str(lr_clustering)
                           + ".txt", nmi_list, fmt="%.5f")