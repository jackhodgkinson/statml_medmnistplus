# MedMNIST Data Exploration - Python File 
## Package Import 

from tqdm import tqdm

import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt 
import torch
import sklearn
import os 
import random
import itertools
from PIL import Image

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

import torch.nn as nn
import torch.optim as optim
import torch.utils.data as data
from data import Dataset
import torchvision.transforms as transforms

from medmnist.info import INFO, HOMEPAGE, DEFAULT_ROOT

try:
    from collections.abc import Sequence
except ImportError:
    from collections import Sequence


## MedMNISTv2 code to load the datasetst 
class MedMNIST(Sequence):

    flag = ...

    def __init__(
        self,
        split,
        transform=None,
        target_transform=None,
        download=False,
        as_rgb=False,
        root=DEFAULT_ROOT,
        size=None,
        mmap_mode=None
    ):
        ''' 
        Args:

            split (str, required): 'train', 'val' or 'test'
            transform (callable, optional): data transformation
            target_transform (callable, optional): target transformation
            size (int, optional): The size of the returned images. If None, use MNIST-like 28. Default: None.
            mmap_mode (str, optional): If not None, read image arrays from the disk directly. This is useful to set `mmap_mode='r'` to save memory usage when the dataset is large (e.g., PathMNIST-224). Default: None.

        '''

        if (size is None) or (size == 28):
            self.size = 28
            self.size_flag = ""
        else:
            assert size in self.available_sizes
            self.size = size
            self.size_flag = f"_{size}"


        self.info = INFO[self.flag]

        if root is not None and os.path.exists(root):
            self.root = root
        else:
            raise RuntimeError("Failed to setup the default `root` directory. " +
                               "Please specify and create the `root` directory manually.")

        if download:
            self.download()

        if not os.path.exists(
                os.path.join(self.root, "{}.npz".format(self.flag))):
            raise RuntimeError('Dataset not found.' +
                               ' You can use download=True to download it')

        npz_file = np.load(
            os.path.join(self.root, f"{self.flag}{self.size_flag}.npz"),
            mmap_mode=mmap_mode,
        )

        self.split = split
        self.transform = transform
        self.target_transform = target_transform
        self.as_rgb = as_rgb

        if self.split in ["train", "val", "test"]:
            self.imgs = npz_file[f"{self.split}_images"]
            self.labels = npz_file[f"{self.split}_labels"]
        else:
            raise ValueError

    def __len__(self):
        return self.imgs.shape[0]

    def __repr__(self):
        '''Adapted from torchvision.ss'''
        _repr_indent = 4
        head = f"Dataset {self.__class__.__name__} ({self.flag})"
        body = [f"Number of datapoints: {self.__len__()}"]
        body.append(f"Root location: {self.root}")
        body.append(f"Split: {self.split}")
        body.append(f"Task: {self.info['task']}")
        body.append(f"Number of channels: {self.info['n_channels']}")
        body.append(f"Meaning of labels: {self.info['label']}")
        body.append(f"Number of samples: {self.info['n_samples']}")
        body.append(f"Description: {self.info['description']}")
        body.append(f"License: {self.info['license']}")

        lines = [head] + [" " * _repr_indent + line for line in body]
        return '\n'.join(lines)

    def download(self):
        try:
            from torchvision.datasets.utils import download_url

            download_url(
                url=self.info[f"url{self.size_flag}"],
                root=self.root,
                filename=f"{self.flag}{self.size_flag}.npz",
                md5=self.info[f"MD5{self.size_flag}"],
            )
        except:
            raise RuntimeError('Something went wrong when downloading! ' +
                               'Go to the homepage to download manually. ' +
                               HOMEPAGE)

    @staticmethod
    def _collate_fn(data):
        xs = []
        ys = []
        for x, y in data:
            xs.append(np.array(x))
            ys.append(y)
        return np.array(xs), np.array(ys)


class MedMNIST2D(MedMNIST):
    available_sizes = [28, 64, 128, 224]

    def __getitem__(self, index):
        '''
        return: (without transform/target_transofrm)
            img: PIL.Image
            target: np.array of `L` (L=1 for single-label)
        '''
        img, target = self.imgs[index], self.labels[index].astype(int)
        img = Image.fromarray(img)

        if self.as_rgb:
            img = img.convert('RGB')

        if self.transform is not None:
            img = self.transform(img)

        if self.target_transform is not None:
            target = self.target_transform(target)

        return img, target

    def save(self, folder, postfix="png", write_csv=True):

        from medmnist.utils import save2d

        save2d(
            imgs=self.imgs,
            labels=self.labels,
            img_folder=os.path.join(folder, f"{self.flag}{self.size_flag}"),
            split=self.split,
            postfix=postfix,
            csv_path=os.path.join(folder, f"{self.flag}{self.size_flag}.csv") if write_csv else None
        )

    def montage(self, length=20, replace=False, save_folder=None):
        from medmnist.utils import montage2d

        n_sel = length * length
        sel = np.random.choice(self.__len__(), size=n_sel, replace=replace)

        montage_img = montage2d(imgs=self.imgs,
                                n_channels=self.info['n_channels'],
                                sel=sel)

        if save_folder is not None:
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
            montage_img.save(os.path.join(save_folder,
                                          f"{self.flag}{self.size_flag}_{self.split}_montage.jpg"))

        return montage_img


class MedMNIST3D(MedMNIST):
    available_sizes = [28, 64]

    def __getitem__(self, index):
        '''
        return: (without transform/target_transofrm)
            img: an array of 1x28x28x28 or 3x28x28x28 (if `as_RGB=True`), in [0,1]
            target: np.array of `L` (L=1 for single-label)
        '''
        img, target = self.imgs[index], self.labels[index].astype(int)

        img = np.stack([img/255.]*(3 if self.as_rgb else 1), axis=0)

        if self.transform is not None:
            img = self.transform(img)

        if self.target_transform is not None:
            target = self.target_transform(target)

        return img, target

    def save(self, folder, postfix="gif", write_csv=True):
        from medmnist.utils import save3d

        assert postfix == "gif"

        save3d(
            imgs=self.imgs,
            labels=self.labels,
            img_folder=os.path.join(folder, f"{self.flag}{self.size_flag}"),
            split=self.split,
            postfix=postfix,
            csv_path=os.path.join(folder, f"{self.flag}{self.size_flag}.csv") if write_csv else None
        )

    def montage(self, length=20, replace=False, save_folder=None):
        assert self.info['n_channels'] == 1

        from medmnist.utils import montage3d, save_frames_as_gif

        n_sel = length * length
        sel = np.random.choice(self.__len__(), size=n_sel, replace=replace)

        montage_frames = montage3d(imgs=self.imgs,
                                   n_channels=self.info['n_channels'],
                                   sel=sel)

        if save_folder is not None:
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)

            save_frames_as_gif(montage_frames,
                               os.path.join(save_folder,
                                            f"{self.flag}{self.size_flag}_{self.split}_montage.gif"))

        return montage_frames


class PathMNIST(MedMNIST2D):
    flag = "pathmnist"


class OCTMNIST(MedMNIST2D):
    flag = "octmnist"


class PneumoniaMNIST(MedMNIST2D):
    flag = "pneumoniamnist"


class ChestMNIST(MedMNIST2D):
    flag = "chestmnist"


class DermaMNIST(MedMNIST2D):
    flag = "dermamnist"


class RetinaMNIST(MedMNIST2D):
    flag = "retinamnist"


class BreastMNIST(MedMNIST2D):
    flag = "breastmnist"


class BloodMNIST(MedMNIST2D):
    flag = "bloodmnist"


class TissueMNIST(MedMNIST2D):
    flag = "tissuemnist"


class OrganAMNIST(MedMNIST2D):
    flag = "organamnist"


class OrganCMNIST(MedMNIST2D):
    flag = "organcmnist"


class OrganSMNIST(MedMNIST2D):
    flag = "organsmnist"


class OrganMNIST3D(MedMNIST3D):
    flag = "organmnist3d"


class NoduleMNIST3D(MedMNIST3D):
    flag = "nodulemnist3d"


class AdrenalMNIST3D(MedMNIST3D):
    flag = "adrenalmnist3d"


class FractureMNIST3D(MedMNIST3D):
    flag = "fracturemnist3d"


class VesselMNIST3D(MedMNIST3D):
    flag = "vesselmnist3d"


class SynapseMNIST3D(MedMNIST3D):
    flag = "synapsemnist3d"


# backward-compatible
OrganMNISTAxial = OrganAMNIST
OrganMNISTCoronal = OrganCMNIST
OrganMNISTSagittal = OrganSMNIST


def get_loader(dataset, batch_size):
    total_size = len(dataset)
    print('Size', total_size)
    index_generator = shuffle_iterator(range(total_size))
    while True:
        data = []
        for _ in range(batch_size):
            idx = next(index_generator)
            data.append(dataset[idx])
        yield dataset._collate_fn(data)


def shuffle_iterator(iterator):
    # iterator should have limited size
    index = list(iterator)
    total_size = len(index)
    i = 0
    random.shuffle(index)
    while True:
        yield index[i]
        i += 1
        if i >= total_size:
            i = 0
            random.shuffle(index)

## Functions for Analyses 
### Setup 
datasets = {}
features = {}
labels = {}

### Function to name datasets 
def dataset_namer(input_name, suffix, size=''): #size as optional parameter!
    global string
    if size != '':
        string = f"{input_name}_{suffix}_{size}"
    else:
        string = f"{input_name}_{suffix}"
        
    return string

### Function to generate MedMNIST datasets
def medmnist_generator(data_flag, split, size):

    # Taken from MedMNIST v2 GitHub
    info = INFO[data_flag]
    task = info['task']
    n_channels = info['n_channels']
    n_classes = len(info['label'])

    DataClass = getattr(medmnist, info['python_class'])

    # Preprocessing
    data_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[.5], std=[.5])
        ])
    
    # Use of Dataset_Namer function to encode outputs
    name = dataset_namer(data_flag, split, size)
    
    global datasets
    
    # Splits each dataset into training, validation and testing dataset. 
    value = DataClass(split=split, size=int(size), transform=data_transform,download=True) 
    entry = {name: value}
    datasets.update(entry)
    
    globals()[name] = value

### Function to retrieve variable name as a string
def get_var_name(input_var):
    for name, var in globals().items():
        if var is input_var:
            return name
    return None

### Function to extract features and labels from MedMNIST image data
def features_labels(key, value):   

    # Extract features and transform to torch
    X = value.imgs
    X = X.reshape(X.shape[0], -1)
    X = torch.from_numpy(X)
    
    # Extract labels and transform to torch
    y = value.labels
    y = np.ravel(y)
    y = torch.from_numpy(y)
    
    # Name feature and labels datasets
    f_name = dataset_namer(key, "features", '')
    l_name = dataset_namer(key, "labels", '')
    
    globals()[f_name] = X
    globals()[l_name] = y
    
    global features, labels

    f_entry = {f_name: X}
    features.update(f_entry) 

    l_entry = {l_name: y}
    labels.update(l_entry)

### Function to split dictionaries by specified split
def dict_split(dictionary, split):
    
    new_dict = {}
    
    for key, value in dictionary.items():
        if split in key:
            name = dataset_namer(split, get_var_name(dictionary))
            new_dict[key] = value
            globals()[name] = new_dict    

### Function to transform data into dataloader form for deep learning 
def data_loader(name, batch_size):
    name = dataset_namer(name, "loader", '')
    if 'train' in name:
        globals()[name] = data.DataLoader(dataset = name, batch_size = BATCH_SIZE, shuffle = True)
    else: 
        globals()[name] = data.DataLoader(dataset = name, batch_size = BATCH_SIZE, shuffle = False)

### Function for principal component analysis (linear and non-linear kernels)
def pca(data, normalise='Yes', kernel='No',kernel_type='linear'):
    
    ds_name = variable_name(data)
    
    if kernel == 'No':
    
        if normalise == 'Yes':

            name = dataset_namer(ds_name, "normalised_pca", '')

            def pca_normalise(data):

                data = StandardScaler().fit_transform(data)
                feature_cols = ['feature'+str(i) for i in range(data.shape[1])]    
                normalised_features = pd.DataFrame(data,columns=feature_cols)
                data = normalised_features

                return data

            data = pca_normalise(data)

        elif normalise == 'No': 
            name = dataset_namer(ds_name, "pca", '')

        else: 
            print("ERROR: Invalid input to normalise parameter. Please choose 'Yes' or 'No'.")


        pca = PCA()
        principalComponents = pca.fit_transform(data)
        pca_cols = ['pc'+str(i) for i in range(principalComponents.shape[1])]

        value = pd.DataFrame(data = principalComponents, columns = pca_cols)
        entry = {name: value}
        datasets.update(entry)
        globals()[name] = value
        
    elif kernel == 'Yes':
    
        if normalise == 'Yes':

            name = dataset_namer(ds_name, "normalised_kernel_pca", '')

            def pca_normalise(data):

                data = StandardScaler().fit_transform(data)
                feature_cols = ['feature'+str(i) for i in range(data.shape[1])]    
                normalised_features = pd.DataFrame(data,columns=feature_cols)
                data = normalised_features

                return data

            data = pca_normalise(data)

        elif normalise == 'No': 
            name = dataset_namer(ds_name, "kernel_pca", '')

        else: 
            print("ERROR: Invalid input to normalise parameter. Please choose 'Yes' or 'No'.")


        kernel_pca = KernelPCA(kernel=kernel_type)
        kernel_principalComponents = kernel_pca.fit_transform(data)
        kernel_pca_cols = ['pc'+str(i) for i in range(kernel_principalComponents.shape[1])]

        value = pd.DataFrame(data = kernel_principalComponents, columns = kernel_pca_cols)
        entry = {name: value}
        datasets.update(entry)
        globals()[name] = value
    
    else:
        print("ERROR: Invalid input to kernel parameter. Please choose 'Yes' or 'No'.")

## Generating the Data
### Specifying Function Inputs

data_flag = ('pathmnist','dermamnist','breastmnist')
split = ('train','test','val')
size = (28,64,128,224)

### Generate Datasets
for a, b, c in itertools.product(data_flag, split, size): 
    medmnist_generator(a,b,c)

### Show dataset information
#### Show information for PathMNIST
print(pathmnist_train_28)
print(pathmnist_train_64)
print(pathmnist_train_128)
print(pathmnist_train_224)

#### Show information for DermaMNIST
print(dermamnist_train_28)
print(dermamnist_train_64)
print(dermamnist_train_128)
print(dermamnist_train_224)

#### Show information for BreastMNIST
print(breastmnist_train_28)
print(breastmnist_train_64)
print(breastmnist_train_128)
print(breastmnist_train_224)   

### Generate Data Samples
#### Generate 7x7 grid (49 samples) original low resolution images
breastmnist_train_28.montage(length=7).save("Images/breastmnist_lowres_sample.jpeg")
pathmnist_train_28.montage(length=7).save("Images/pathmnist_lowres_sample.jpeg")
dermamnist_train_28.montage(length=7).save("Images/dermamnist_lowres_sample.jpeg")

#### Generate 7x7 grid (49 samples) highest resolution images
breastmnist_train_224.montage(length=7).save("Images/breastmnist_highres_sample.jpeg")
pathmnist_train_224.montage(length=7).save("Images/pathmnist_highres_sample.jpeg")
dermamnist_train_224.montage(length=7).save("Images/dermamnist_highres_sample.jpeg")

#### Resolution Comparison 
dermamnist_train_28.montage(length=7).save("Images/res_comp1.jpeg")
dermamnist_train_64.montage(length=7).save("Images/res_comp2.jpeg")
dermamnist_train_128.montage(length=7).save("Images/res_comp3.jpeg")
dermamnist_train_224.montage(length=7).save("Images/res_comp4.jpeg")

### Extract Features and Labels from each dataset
for key, value in datasets.items():
    features_labels(key, value)

### Split features and labels by train/test/val
for i in split:
    dict_split(features, i)
    dict_split(labels, i)

## Pre-processing 
### Quantitites needed 
NUM_EPOCHS = 3
BATCH_SIZE = 128
lr = 0.001

## Model Fitting - Pre-Feature Selection
### Linear Discriminant Analysis 

## Deep Learning 
### Transform data into dataloader form 
for key in datasets.keys():
    data_loader(key, BATCH_SIZE)