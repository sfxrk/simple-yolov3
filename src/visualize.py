import pickle
from random import sample

import matplotlib.image as mpimg
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf

from src import constants, helpers


def add_label_to_plot(ax, c, label, x_min, y_min):
    color = (0, 0, 0)
    if use_white_text(c):
        color = (1, 1, 1)
    ax.text(x_min, y_min - 2, s=label, fontsize=5, bbox=dict(facecolor=c, linewidth=0, boxstyle='square,pad=0'),
            color=color)


def get_colors(annotations: list, labels: list) -> list:
    """ Find the number of unique labels and assign each of them a color from the predefined set randomly """
    for bbox in annotations:
        x_min, y_min, x_max, y_max, label = bbox
        if label not in labels:
            labels.append(label)
    if len(labels) < len(constants.colors):
        colors = np.array(sample(constants.colors, len(labels))) / 255
    else:
        colors = np.array(constants.colors * (int(len(labels) / len(constants.colors)) + 1)) / 255
    return colors


def load_tensorboard_image(image, groundtruth_ann: list, annotations: list, probs: list, dataset_name: str):
    labels_map_dict = helpers.get_labels_dict(dataset_name)
    # Create figure and axes
    fig, ax = plt.subplots(1)
    labels = []

    # Get the unique labels to assign a color to each
    colors = get_colors(groundtruth_ann + annotations, labels)
    separation = 10
    # Concatenate the same image with a white space in between
    new_image = np.concatenate((image, 255 * np.ones((image.shape[0], separation, 3)).astype(np.int32), image), axis=1)
    # Load the original image with its groundtruth annotations
    ax.imshow(new_image)
    for i, bbox in enumerate(groundtruth_ann):
        if sum(bbox) == 0:
            continue
        plot_image_annotations_help(ax=ax, bbox=bbox, colors=colors, labels=labels, labels_map=labels_map_dict,
                                    show_axis=False)
    # Load the predicted labels
    for i, bbox in enumerate(annotations):
        if sum(bbox) == 0:
            continue
        # Move the bounding boxes to the left to align with the second image
        bbox[:3] = (np.array(bbox[:3]) + (separation + image.shape[1], 0, separation + image.shape[1])).tolist()
        plot_image_annotations_help(ax=ax, bbox=bbox, colors=colors, labels=labels, labels_map=labels_map_dict,
                                    show_axis=False, probability=probs[i])
    # Workaround for returning the image with the annotations as a tensor, save and load it.
    plt.axis('off')
    plt.savefig('/tmp/tb_img.png', dpi=500, bbox_inches='tight', pad_inches=0)
    plt.close()
    img = tf.image.decode_jpeg(open('/tmp/tb_img.png', 'rb').read(), channels=3)
    img = tf.cast(tf.image.resize(img, (400, 1200)), tf.uint8)
    return img


def plot_history(history: dict, figs_path: str = None, show_figures: bool = True):
    if figs_path is None and not show_figures:
        return
    n_epochs = len(history['loss'])
    epochs = [i + 1 for i in range(n_epochs)]
    plt.plot(epochs, history['loss'], label='Train loss')
    plt.plot(epochs, history['val_loss'], label='Validation loss')
    plt.title('Losses')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    if figs_path:
        plt.savefig(figs_path + 'loss.png')
    if show_figures:
        plt.show()

    if 'accuracy' in history:
        plt.figure()
        plt.plot(epochs, history['accuracy'], label='Train accuracy')
        plt.plot(epochs, history['val_accuracy'], label='Validation accuracy')
        plt.title('Accuracy')
        plt.xlabel('epochs')
        plt.ylabel('accuracy')
        plt.legend()
        if figs_path:
            plt.savefig(figs_path + 'accuracy.png')
        if show_figures:
            plt.show()

    if 'learning_rates' in history:
        plt.figure()
        plt.plot(epochs, history['learning_rates'])
        plt.xlabel('Epoch')
        plt.ylabel('Learning rate')
        plt.title('Learning rate cosine decay')
        plt.legend()
        if figs_path:
            plt.savefig(figs_path + 'lr_schedule.png')
        if show_figures:
            plt.show()


def plot_history_from_pickle_path(path):
    history = pickle.load(open(path, "rb"))
    plot_history(history)


def plot_image_annotations(image_path: str, annotations: list, labels_map_dict: dict, probs: list = None,
                           title: str = "", output_path: str = None):
    """
    Plot one image with its bounding boxes
    :param image_path: path to the image
    :param annotations: list with the annotations [[x_min, y_min, x_max, y_max, label], [...], ...]
    :param labels_map_dict: dictionary with key the label id and value the label value
    :param probs: list with the probability of each label
    :param title: title of the plot
    :param output_path: path to save the figure. If none then it is not saved.
    """
    # Create figure and axes
    fig, ax = plt.subplots(1)

    # Display the image
    ax.imshow(mpimg.imread(image_path))
    labels = []

    # Get the unique labels to assign a color to each
    colors = get_colors(annotations, labels)

    for i, bbox in enumerate(annotations):
        plot_image_annotations_help(ax, bbox, colors, labels, labels_map_dict, False,
                                    probability=(None if probs is None else probs[i]))
    plt.title(title)
    if output_path:
        plt.savefig(output_path)
    plt.show()


def plot_images_annotations_box(images_path: list, annotations: list, labels_map: dict, title: str = ""):
    """ This code only plots 4 images in a 2x2 set. Tailor it to your needs! """
    if len(images_path) != len(annotations) != 4:
        raise Exception("Each image needs to have their annotations!")

    # Create figure and axes
    fig, ax = plt.subplots(2, 2)
    i = 0
    for index, path in enumerate(images_path):
        j = index % 2
        if index == 2:
            i = 1
        # Display the image
        ax[i, j].imshow(mpimg.imread(path))
        labels = []
        colors = get_colors(annotations[index], labels)

        # Plot the bounding boxes and labels
        for bbox in annotations[index]:
            plot_image_annotations_help(ax[i, j], bbox, colors, labels, labels_map, False)
        ax[i, j].set_title(path.split('/')[-1], fontsize=7)

    plt.subplots_adjust(wspace=0, hspace=0)
    fig.suptitle(title)
    plt.show()


def plot_image_annotations_help(ax, bbox, colors, labels, labels_map, show_axis, probability=None):
    """ Plot the image and its bounding box """
    x_min, y_min, x_max, y_max, label = bbox
    c = colors[labels.index(label)]
    # if label == 43:
    #     a = 1
    label = labels_map[str(label)]
    if probability is not None:
        label += ' ' + '{:.2f}'.format(probability * 100) + '%'
    # Create a Rectangle patch
    rect = patches.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min, linewidth=1,
                             edgecolor=c, facecolor='none')
    add_label_to_plot(ax, c, label, x_min, y_min)
    # Add the patch to the Axes
    ax.add_patch(rect)
    if not show_axis:
        ax.axis('off')


def plot_image_annotations_simple(image_path: str, title: str = ""):
    """ the image file should finish with: /dataset_name/train_val_test/image"""
    info = image_path.split('/')
    dataset_name, train_val_test, image = info[-3:]
    annotations = helpers.get_annotations_dict(dataset_name, train_val_test)[image]
    labels_map_dict = helpers.get_labels_dict(dataset_name)
    plot_image_annotations(image_path, annotations, labels_map_dict, title=title)


def plot_images_and_boxes(img, boxes, switch=False, multi=True, i=None, title="", dataset_name=None, colors=None):
    if type(boxes) != np.ndarray:
        boxes = np.array(boxes)
    fig, ax = plt.subplots(1)
    ax.imshow(img)
    img_shape = np.array([img.shape[1], img.shape[0], img.shape[1], img.shape[0]])
    if dataset_name:
        labels_map = helpers.get_labels_dict(dataset_name)

    labels = []
    colors = get_colors(boxes, labels)

    if switch:
        boxes[:, [0, 1, 2, 3]] = boxes[:, [1, 0, 3, 2]]

    for bbox in boxes:
        original = bbox
        if multi:
            bbox = [int(elem) for elem in list(bbox[:4] * img_shape)] + ([int(bbox[-1])] if len(bbox) == 5 else [])
        if np.sum(bbox[:4]) == 0:
            continue
        # print("Box added:", bbox, "original", original)
        rect = patches.Rectangle((bbox[0], bbox[1]), bbox[2] - bbox[0], bbox[3] - bbox[1], linewidth=1,
                                 edgecolor=colors[labels.index(bbox[-1])],
                                 facecolor='none')
        if dataset_name and len(bbox) == 5:
            add_label_to_plot(ax, colors[labels.index(bbox[-1])], labels_map[str(bbox[-1])], bbox[0], bbox[1])

        plt.scatter(bbox[0], bbox[1], c='r', marker='x')
        plt.scatter(bbox[2], bbox[3], c='g', marker='x')
        ax.add_patch(rect)
    plt.title(title)
    if i is not None:
        plt.savefig('{:03d}.png'.format(i))
    plt.show()
    if i is not None:
        return i + 1
    else:
        return i


def use_white_text(color):
    """ Following W3C guidelines, when the luminance is bigger than 0.179, the text should be blank,
        white otherwise. """
    luminance = 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]
    return luminance <= 0.179


def visualize_box(boxes, image, i):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.imshow(image)
    for b in boxes:
        ax.add_patch(plt.Polygon(b, fill=None, edgecolor='r', linewidth=3))
        # ax.add_patch(mpatches.Polygon(b, True))
    # ax.autoscale_view()
    plt.savefig('{:03d}.png'.format(i))
    plt.show()
