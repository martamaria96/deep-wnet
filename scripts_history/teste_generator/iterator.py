
# Keras-contrib image iterators

import numpy as np

from keras.preprocessing.image import Iterator
from keras import backend as K


class ImageDataIterator(Iterator):

    def __init__(self, xy_provider, n, image_data_generator,
                 batch_size=32, shuffle=False, seed=None,
                 data_format=None):

        # Check xy_provider and store the first values
        if data_format is None:
            if not hasattr(K, 'image_data_format') and hasattr(K, 'image_dim_ordering'):
                data_format = "channels_last" if K.image_dim_ordering() == "tf" else "channels_first"
            else:
                data_format = K.image_data_format()

        ret = next(xy_provider)
        assert isinstance(ret, list) or isinstance(ret, tuple) and 2 <= len(ret) <= 3, \
            "Generator xy_provider should yield a list/tuple of (image, mask) or (image, mask, info)"

        x, y, info = ret if len(ret) > 2 else (ret[0], ret[1], None)
        self._check_x_format(x, data_format=data_format)
        if y is not None:
            self._check_y_format(y, data_format=data_format)
        self._first_xy_provider_ret = (x, y, info)

        super(ImageDataIterator, self).__init__(n, batch_size, shuffle, seed)

        self.data_format = data_format
        self.xy_provider = xy_provider
        self._process = None
        self._image_data_generator = None
        self.image_data_generator = image_data_generator

    @property
    def image_data_generator(self):
        return self._image_data_generator

    @image_data_generator.setter
    def image_data_generator(self, generator):
        self._image_data_generator = generator
        if self._image_data_generator is None:
            self._process = self._empty_process
        elif hasattr(self._image_data_generator, 'process'):
            self._process = self.image_data_generator.process
        else:
            self._process = self._default_image_data_generator_process

    def _empty_process(self, img, target):
        return img, target

    def _default_image_data_generator_process(self, img, target):
        img = self.image_data_generator.random_transform(img)
        return self.image_data_generator.standardize(img), target

    def _check_x_format(self, x, **kwargs):
        ImageDataIterator._check_img_format(x, **kwargs)

    def _check_y_format(self, y, **kwargs):
        assert isinstance(y, np.ndarray), "Y should be an ndarray, one-hot encoded vector"

    def _create_y_batch(self, current_batch_size, x, y):

        return np.zeros((current_batch_size, ) + y.shape, dtype=y.dtype)

    @staticmethod
    def _check_img_format(img, data_format):
        assert len(img.shape) == 3, "Image should be a 3D ndarray"
        channel_index = -1 if data_format == 'channels_last' else 0
        assert min(img.shape) == img.shape[channel_index], \
            "Wrong data format: image shape '{}' and data format '{}'".format(img.shape, data_format)

    def next(self):

        with self.lock:
            print(self.index_generator)
            index_array, current_index, current_batch_size = next(self.index_generator)

        if self._first_xy_provider_ret is not None:
            x, y, info = self._first_xy_provider_ret
            self._first_xy_provider_ret = None
        else:
            ret = next(self.xy_provider)
            x, y, info = ret if len(ret) > 2 else (ret[0], ret[1], None)

        batch_x = np.zeros((current_batch_size,) + x.shape, dtype=K.floatx())
        # Y can be None if ImageDataIterator is used to iterate over test data
        if y is not None:
            batch_y = self._create_y_batch(current_batch_size, x=x, y=y)
        else:
            batch_y = np.empty((current_batch_size, ), dtype=object)
        batch_info = np.empty((current_batch_size,), dtype=object)
        batch_x[0], batch_y[0] = self._process(x, y)
        batch_info[0] = info

        for i, j in enumerate(index_array[1:]):
            ret = next(self.xy_provider)
            x, y, info = ret if len(ret) > 2 else (ret[0], ret[1], None)
            self._check_x_format(x, data_format=self.data_format)
            if y is not None:
                self._check_y_format(y, data_format=self.data_format)
            batch_x[i + 1], batch_y[i + 1] = self._process(x, y)
            batch_info[i + 1] = info

        if info is not None:
            return batch_x, batch_y, batch_info
        return batch_x, batch_y


class ImageMaskIterator(ImageDataIterator):


    def __init__(self, *args, **kwargs):
        super(ImageMaskIterator, self).__init__(*args, **kwargs)

    def _check_x_format(self, x, **kwargs):
        ImageDataIterator._check_img_format(x, **kwargs)

    def _check_y_format(self, y, **kwargs):
        ImageDataIterator._check_img_format(y, **kwargs)

    def _create_y_batch(self, current_batch_size, x, y):
        return np.zeros((current_batch_size,) + y.shape, dtype=K.floatx())
