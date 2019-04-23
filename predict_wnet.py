from train_wnet import wnet_weights, get_model, PATCH_SZ, N_CLASSES
from patchify import patchify, unpatchify
from scipy import stats
from sklearn.metrics import classification_report, accuracy_score
from itertools import product
import tifffile as tiff
import gc
import sys
import numpy as np
import tensorflow as tf

gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=1)
sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options))
'''
def check_output(step, dataset):
    model = get_model()
    model.load_weights(wnet_weights)
    if dataset == 'p':
        test = ['2_13','2_14','3_13','3_14','4_13','4_14','4_15','5_13','5_14','5_15','6_13','6_14','6_15','7_13']
        path_img = '/home/mdias/deep-wnet/potsdam/Images_lab/top_potsdam_{}_RGB.tif'
        path_mask = '/home/mdias/deep-wnet/potsdam/Masks/top_potsdam_{}_label.tif'

    elif dataset == 'v':
        test = ['2', '4', '6', '8', '10', '12', '14', '16', '20', '22', '24', '27', '29', '31', '33', '35', '38']
        path_i = './vaihingen/test/Images_lab/top_mosaic_09cm_area{}.tif'
        path_mask = './vaihingen/test/Masks/top_mosaic_09cm_area{}.tif'


    accuracy_all = []
    for test_id in test:
        path_img = path_i.format(test_id)
        img = tiff.imread(path_img)/255
        patch_sz = PATCH_SZ
        patches = patchify(img, (patch_sz, patch_sz, img.ndim), step = step)
        width_window, height_window, z, width_x, height_y, num_channel = patches.shape
        patches = np.reshape(patches, (width_window * height_window,  width_x, height_y, num_channel))
        patches_predict = model.predict(patches, batch_size=1)
        seg_mask, img_rec = patches_predict[0], patches_predict[1]
        dim_x, dim_y, dim = img.shape
        prediction = reconstruct_patches(img_rec, (dim_x, dim_y, dim), step)
        print(img_rec.shape)
        print(wnet_weights)
        print(np.unique(img_rec))
        print('\n\n', np.mean(img_rec))
        tiff.imsave('img_rec.tif', img_rec)
'''
def reconstruct_patches(patches, image_size, step):
    i_h, i_w = image_size[:2]
    p_h, p_w = patches.shape[1:3]
    print('image_size', image_size)
    print('patches shape', patches.shape)
    img = np.zeros(image_size)
    patch_count = np.zeros(image_size)
    # compute the dimensions of the patches array
    n_h = int((i_h - p_h) / step + 1)
    n_w = int((i_w - p_w) / step + 1)
    for p, (i, j) in zip(patches, product(range(n_h), range(n_w))):
        img[i * step:i * step + p_h, j * step:j * step + p_w] += p
    #for p, (i, j) in zip(patches, product(range(n_h), range(n_w))):
        patch_count[i * step:i * step + p_h, j * step:j * step + p_w] += 1
    print('MAX time seen', np.amax(patch_count))
    return img/patch_count

def predict(x, model, patch_sz=160, n_classes=5, step = 142):
    dim_x, dim_y, dim = x.shape
    print('dim', dim_x, dim_y, dim)
    patches = patchify(x, (patch_sz, patch_sz, x.ndim), step = step)
    width_window, height_window, z, width_x, height_y, num_channel = patches.shape
    patches = np.reshape(patches, (width_window * height_window,  width_x, height_y, num_channel))

    predict = model.predict(patches, batch_size=50)
    patches_predict = predict[0]
    image_predict = predict[1]
    #prediction = reconstruct_patches(patches_predict, (dim_x, dim_y, n_classes), step)
    new_image = reconstruct_patches(image_predict, (dim_x, dim_y, dim), step)
    return new_image
    #return prediction, new_image


def picture_from_mask(mask):
    colors = {
        0: [255, 255, 255],   #imp surface
        1: [255, 255, 0],     #car
        2: [0, 0, 255],       #building
        3: [255, 0, 0],       #background
        4: [0, 255, 255],     #low veg
        5: [0, 255, 0]        #tree
    }

    mask_ind = np.argmax(mask, axis=0)
    pict = np.empty(shape=(3, mask.shape[1], mask.shape[2]))
    for cl in range(6):
      for ch in range(3):
        pict[ch,:,:] = np.where(mask_ind == cl, colors[cl][ch], pict[ch,:,:])
    return pict

def mask_from_picture(picture):
  colors = {
      (255, 255, 255): 0,   #imp surface
      (255, 255, 0): 1,     #car
      (0, 0, 255): 2,       #building
      (255, 0, 0): 3,       #background
      (0, 255, 255): 4,     #low veg
      (0, 255, 0): 5        #tree
  }
  picture = picture.transpose([1,2,0])
  mask = np.ndarray(shape=(256*256*256), dtype='int32')
  mask[:] = -1
  for rgb, idx in colors.items():
    rgb = rgb[0] * 65536 + rgb[1] * 256 + rgb[2]
    mask[rgb] = idx

  picture = picture.dot(np.array([65536, 256, 1], dtype='int32'))
  return mask[picture]

def predict_all(step, dataset):
    model = get_model()
    model.load_weights(wnet_weights)

    if dataset == 'p':
        test = ['2_13','2_14','3_13','3_14','4_13','4_14','4_15','5_13','5_14','5_15','6_13','6_14','6_15','7_13']
        path_i = '/home/mdias/deep-wnet/potsdam/Images_lab/top_potsdam_{}_RGB.tif'
        path_m = './potsdam/5_Labels_all/top_potsdam_{}_label.tif'

    elif dataset == 'v':
        test = ['2', '4', '6', '8', '10', '12', '14', '16', '20', '22', '24', '27', '29', '31', '33', '35', '38']
        path_i = './vaihingen/test/Images_lab/top_mosaic_09cm_area{}.tif'
        path_m = './vaihingen/test/Masks/top_mosaic_09cm_area{}.tif'

    accuracy_all = []
    for test_id in test:
        path_img = path_i.format(test_id)
        img = tiff.imread(path_img)
        path_mask = path_m.format(test_id)
        label = tiff.imread(path_mask).transpose([2,0,1])
        gt = mask_from_picture(label)

        #mask, new_image = predict(img, model, patch_sz=PATCH_SZ, n_classes=N_CLASSES, step = step)
        new_image = predict(img, model, patch_sz=PATCH_SZ, n_classes=N_CLASSES, step = step)
        #mask = mask.transpose([2,0,1])
        prediction = picture_from_mask(mask)

        target_labels = ['imp surf', 'car', 'building', 'background', 'low veg', 'tree']
        #y_true = gt.ravel()
        #y_pred = np.argmax(mask, axis=0).ravel()
        #report = classification_report(y_true, y_pred, target_names = target_labels)
        #accuracy = accuracy_score(y_true, y_pred)
        print('\n',test_id)
        #print(report)
        #print('\nAccuracy', accuracy)
        #accuracy_all.append(accuracy)
        #tiff.imsave('./results/prediction_{}.tif'.format(test_id), prediction)
        #tiff.imsave('./results/mask_{}.tif'.format(test_id), mask)
        tiff.imsave('./results/lab/image_{}.tif'.format(test_id), new_image)
        gc.collect()
        gc.collect()
        gc.collect()
        sys.stdout.flush()

    print(accuracy_all)
    print(step,' Accuracy all', sum(accuracy_all)/len(accuracy_all))

step = 80
dataset = 'p'
print(step)
predict_all(step, dataset)
#check_output(step, dataset)
