### draft script - currently COPIED FROM PRAJAY'S vape.utils_func copy on Nov 22
## TODO - Rob to update with current utils_func from Vape

import numpy as np
import tifffile as tf
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import seaborn as sns
import csv
import math
import copy
import io


# # global plotting params
# params = {'legend.fontsize': 'x-large',
#           'axes.labelsize': 'x-large',
#           'axes.titlesize': 'x-large',
#           'xtick.labelsize': 'x-large',
#           'ytick.labelsize': 'x-large'}
# plt.rcParams.update(params)
# sns.set()
# sns.set_style('white')

##### PRAJAY'S FUNCTIONS THAT MIGHT BE APPROP FOR THIS SCRIPT ####### / start

def normalize_dff(arr, threshold_pct=20, threshold_val=None):
    """normalize given array (cells x time) to the mean of the fluorescence values below given threshold. Threshold
    will refer to the that lower percentile of the given trace."""

    if arr.ndim == 1:
        if threshold_val is None:
            a = np.percentile(arr, threshold_pct)
            mean_ = arr[arr < a].mean()
        else:
            mean_ = threshold_val
        # mean_ = abs(arr[arr < a].mean())
        new_array = ((arr - mean_) / mean_) * 100
        if np.isnan(new_array).any() == True:
            Warning('Cell (unknown) contains nan, normalization factor: %s ' % mean_)

    else:
        new_array = np.empty_like(arr)
        for i in range(len(arr)):
            if threshold_val is None:
                a = np.percentile(arr[i], threshold_pct)
            else:
                a = threshold_val
            mean_ = np.mean(arr[i][arr[i] < a])
            new_array[i] = ((arr[i] - mean_) / abs(mean_)) * 100

            if np.isnan(new_array[i]).any() == True:
                print('Warning:')
                print('Cell %d: contains nan' % (i + 1))
                print('      Mean of the sub-threshold for this cell: %s' % mean_)

    return new_array

# calculates average over sliding window for an array
def moving_average(arr, n=4):
    """
    calculates average over sliding window for an array
    :param arr:
    :param n:
    :return:
    """
    ret = np.cumsum(arr)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n - 1:] / n

# finding paths to files with a certain extension
def path_finder(umbrella, *args, is_folder=False):
    '''
    returns the path to the single item in the umbrella folder
    containing the string names in each arg
    is_folder = False if args is ls of files
    is_folder = True if  args is ls of folders
    '''
    # ls of bools, has the function found each argument?
    # ensures two folders / files are not found
    found = [False] * len(args)
    # the paths to the args
    paths = [None] * len(args)

    if is_folder:
        for root, dirs, files in os.walk(umbrella):
            for folder in dirs:
                for i, arg in enumerate(args):
                    if arg in folder:
                        assert not found[i], 'found at least two paths for {},' \
                                             'search {} to find conflicts' \
                            .format(arg, umbrella)
                        paths[i] = os.path.join(root, folder)
                        found[i] = True

    elif not is_folder:
        for root, dirs, files in os.walk(umbrella):
            for file in files:
                for i, arg in enumerate(args):
                    if arg in file:
                        assert not found[i], 'found at least two paths for {},' \
                                             'search {} to find conflicts' \
                            .format(arg, umbrella)
                        paths[i] = os.path.join(root, file)
                        found[i] = True

    print(paths)
    for i, arg in enumerate(args):
        if not found[i]:
            raise ValueError('could not find path to {}'.format(arg))

    return paths

def points_in_circle_np(radius, x0=0, y0=0):
    x_ = np.arange(x0 - radius - 1, x0 + radius + 1, dtype=int)
    y_ = np.arange(y0 - radius - 1, y0 + radius + 1, dtype=int)
    x, y = np.where((x_[:, np.newaxis] - x0) ** 2 + (y_ - y0) ** 2 <= radius ** 2)
    for x, y in zip(x_[x], y_[y]):
        yield x, y

# useful for returning indexes when a
def threshold_detect(signal, threshold):
    '''lloyd russell'''
    thresh_signal = signal > threshold
    thresh_signal[1:][thresh_signal[:-1] & thresh_signal[1:]] = False
    frames = np.where(thresh_signal)
    return frames[0]

# simple ZProfile function for any sized square in the frame (equivalent to ZProfile function in Fiji)
def ZProfile(movie, area_center_coords: tuple = None, area_size: int = -1, plot_trace: bool = True,
             plot_image: bool = True, plot_frame: int = 1, vasc_image: np.array = None, **kwargs):
    """
    from Sarah Armstrong

    Plot a z-profile of a movie, averaged over space inside a square area

    movie = can be np.array of the TIFF stack or a tiff path from which it is read in
    area_center_coords = coordinates of pixel at center of box (x,y)
    area_size = int, length and width of the square in pixels
    plot_frame = which movie frame to take as a reference to plot the area boundaries on
    vasc_image = optionally include a vasculature image tif of the correct dimensions to plot the coordinates on.
    """

    if type(movie) is str:
        movie = tf.imread(movie)
    print('plotting zprofile for TIFF of shape: ', movie.shape)

    # assume 15fps for 1024x1024 movies and 30fps imaging for 512x512 movies
    if movie.shape[1] == 1024:
        img_fps = 15
    elif movie.shape[1] == 512:
        img_fps = 30
    else:
        img_fps = None

    assert area_size <= movie.shape[1] and area_size <= movie.shape[2], "area_size must be smaller than the image"
    if area_size == -1:  # this parameter used to plot whole FOV area
        area_size = movie.shape[1]
        area_center_coords = (movie.shape[1]/2, movie.shape[2]/2)
    assert area_size % 2 == 0, "pls give an even area size"

    x = area_center_coords[0]
    y = area_center_coords[1]
    x1 = int(x - 1 / 2 * area_size)
    x2 = int(x + 1 / 2 * area_size)
    y1 = int(y - 1 / 2 * area_size)
    y2 = int(y + 1 / 2 * area_size)
    smol_movie = movie[:, y1:y2, x1:x2]
    smol_mean = np.nanmean(smol_movie, axis=(1, 2))
    print('|- Output shape for z profile: ', smol_mean.shape)

    if plot_image:
        f, ax1 = plt.subplots()
        ref_frame = movie[plot_frame, :, :]
        if vasc_image is not None:
            assert vasc_image.shape == movie.shape[1:], 'vasculature image has incompatible dimensions'
            ax1.imshow(vasc_image, cmap="binary_r")
        else:
            ax1.imshow(ref_frame, cmap="binary_r")

        rect1 = patches.Rectangle(
            (x1, y1), area_size, area_size, linewidth=1.5, edgecolor='r', facecolor="none")

        ax1.add_patch(rect1)
        ax1.set_title("Z-profile area")
        plt.show()

    if plot_trace:
        if 'figsize' in kwargs:
            figsize = kwargs['figsize']
        else:
            figsize = [10, 4]
        fig, ax2 = plt.subplots(figsize=figsize)
        if img_fps is not None:
            ax2.plot(np.arange(smol_mean.shape[0])/img_fps, smol_mean, linewidth=0.5, color='black')
            ax2.set_xlabel('Time (sec)')
        else:
            ax2.plot(smol_mean, linewidth=0.5, color='black')
            ax2.set_xlabel('frames')
        ax2.set_ylabel('Flu (a.u.)')
        if 'title' in kwargs:
            ax2.set_title(kwargs['title'])
        plt.show()

    return smol_mean


def SaveDownsampledTiff(tiff_path: str = None, stack: np.array = None, group_by: int = 4, save_as: str = None, plot_zprofile: bool = True):
    """
    Create and save a downsampled version of the original tiff file. Original tiff file can be given as a numpy array stack
    or a str path to the tiff.

    :param tiff_path: path to the tiff to downsample
    :param stack: numpy array stack of the tiff file already read in
    :param group_by: specified interval for grouped averaging of the TIFF
    :param save_as: path to save the downsampled tiff to, if none provided it will save to the same directory as the provided tiff_path
    :param plot_zprofile: if True, plot the zaxis profile using the full TIFF stack provided.
    :return: numpy array containing the downsampled TIFF stack
    """
    print('downsampling of tiff stack...')

    if save_as is None:
        assert tiff_path is not None, "please provide a save path to save_as"
        save_as = tiff_path[:-4] + '_downsampled.tif'

    if stack is None:
        # open tiff file
        print('|- working on... %s' % tiff_path)
        stack = tf.imread(tiff_path)

    resolution = stack.shape[1]

    # plot zprofile of full TIFF stack
    if plot_zprofile:
        ZProfile(movie=stack, plot_image=True, title=tiff_path)

    # downsample to 8-bit
    stack8 = np.full_like(stack, fill_value=0)
    for frame in np.arange(stack.shape[0]):
        stack8[frame] = convert_to_8bit(stack[frame], 0, 255)

    # stack8 = stack

    # grouped average by specified interval
    num_frames = stack8.shape[0] // group_by
    # avgd_stack = np.empty((num_frames, resolution, resolution), dtype='uint16')
    avgd_stack = np.empty((num_frames, resolution, resolution), dtype='uint8')
    frame_count = np.arange(0, stack8.shape[0], group_by)
    for i in np.arange(num_frames):
        frame = frame_count[i]
        avgd_stack[i] = np.mean(stack8[frame:frame + group_by], axis=0)

    avgd_stack = avgd_stack.astype(np.uint8)

    # bin down to 512 x 512 resolution if higher resolution
    shape = np.shape(avgd_stack)
    if shape[1] != 512:
        # input_size = avgd_stack.shape[1]
        # output_size = 512
        # bin_size = input_size // output_size
        # final_stack = avgd_stack.reshape((shape[0], output_size, bin_size,
        #                                   output_size, bin_size)).mean(4).mean(2)
        final_stack = avgd_stack
    else:
        final_stack = avgd_stack

    # write output
    print("\nsaving %s to... %s" % (final_stack.shape, save_as))
    tf.imwrite(save_as, final_stack, photometric='minisblack')

    return final_stack


def subselect_tiff(tiff_path: str = None, tiff_stack: np.array = None, select_frames: tuple = (0, 0), save_as: str = None):
    if tiff_stack is None:
        # open tiff file
        print('running subselecting tiffs')
        print('|- working on... %s' % tiff_path)
        tiff_stack = tf.imread(tiff_path)

    stack_cropped = tiff_stack[select_frames[0]:select_frames[1]]

    # stack8 = convert_to_8bit(stack_cropped)

    if save_as is not None:
        tf.imwrite(save_as, stack_cropped, photometric='minisblack')

    return stack_cropped


def make_tiff_stack(sorted_paths: list, save_as: str):
    """
    read in a bunch of tiffs and stack them together, and save the output as the save_as

    :param sorted_paths: ls of string paths for tiffs to stack
    :param save_as: .tif file path to where the tif should be saved
    """

    num_tiffs = len(sorted_paths)
    print('working on tifs to stack: ', num_tiffs)

    with tf.TiffWriter(save_as, bigtiff=True) as tif:
        for i, tif_ in enumerate(sorted_paths):
            with tf.TiffFile(tif_, multifile=True) as input_tif:
                data = input_tif.asarray()
            msg = ' -- Writing tiff: ' + str(i + 1) + ' out of ' + str(num_tiffs)
            print(msg, end='\r')
            tif.save(data)


def convert_to_8bit(img, target_type_min=0, target_type_max=255):
    """
    :param img:
    :param target_type:
    :param target_type_min:
    :param target_type_max:
    :return:
    """
    imin = img.min()
    imax = img.max()

    a = (target_type_max - target_type_min) / (imax - imin)
    b = target_type_max - a * imax
    new_img = (a * img + b).astype(np.uint8)
    return new_img


##### PRAJAY'S FUNCTIONS THAT MIGHT BE APPROP FOR THIS SCRIPT ####### / end

def _check_path_exists(path_arg: str, path: str):
    try:
        assert os.path.exists(path), f"{path_arg} path not found: {path}"
        return True
    except AssertionError:
        return False

def clean_lfp_signal(paq, input_array: str, chan_name: str = 'voltage', plot=False):
    '''
    the idea is to use EphysViewer.m in matlab to view .paq files and then from there export an excel file that
    will contain paired sets of timevalues that are the start and end of the signal to clean up.

    note: "clean up" does not mean to remove the signal values but instead to set them to a constant value that
    will connect the end of the pre-clean signal and post-clean signal, so that it returns a continuous signal of the
    same length as the original signal.

    :param plot: to make plot of the fixed up LFP signal or not
    :param chan_name: channel name in paq file that contains the LFP series
    :param paq: paq file containing the LFP series
    :param input_array: path to .mat file to read that contains the timevalues for signal to remove
    :return: cleaned up LFP signal
    '''

    measurements = io.loadmat(input_array)

    lfp_series = paq['data'][paq['chan_names'].index(chan_name)]
    for set in range(len(measurements['PairedMeasures'])):
        # calculate the sample value for begin and end of the set
        begin = int(measurements['PairedMeasures'][set][3][0][0] * paq['rate'])
        end = int(measurements['PairedMeasures'][set][5][0][0] * paq['rate'])

        lfp_series[begin:end] = lfp_series[begin - 1]  # set the signal value to equal the voltage value just before

    # detrend the LFP signal
    signal.detrend(lfp_series)

    if plot:
        plt.figure(figsize=[40, 4])
        plt.plot(lfp_series, linewidth=0.2)
        plt.suptitle('LFP voltage')
        plt.show()

    return lfp_series
    # replot the LFP signal


def intersect(lst1, lst2):
    return list(set(lst1) & set(lst2))


def dfof(arr):
    '''takes 1d ls or array or 2d array and returns dfof array of same
       dim (JR 2019) This is extraordinarily slow, use dfof2'''

    if type(arr) is list or type(arr) == np.ndarray and len(arr.shape) == 1:
        F = np.mean(arr)
        dfof_arr = [((f - F) / F) * 100 for f in arr]

    elif type(arr) == np.ndarray and len(arr.shape) == 2:
        dfof_arr = []
        for trace in arr:
            F = np.mean(trace)
            dfof_arr.append([((f - F) / F) * 100 for f in trace])

    else:
        raise NotImplementedError('input type not recognised')

    return np.array(dfof_arr)


def dfof2(flu):
    '''
    delta f over f, this function is orders of magnitude faster
    than the dumb one above takes input matrix flu
    (num_cells x num_frames)
    (JR 2019)

    '''

    flu_mean = np.mean(flu, 1)
    flu_mean = np.reshape(flu_mean, (len(flu_mean), 1))
    return (flu - flu_mean) / flu_mean


def get_tiffs(path):
    tiff_files = []
    for file in os.listdir(path):
        if file.endswith('.tif') or file.endswith('.tiff'):
            tiff_files.append(os.path.join(path, file))

    return tiff_files


def s2p_loader(s2p_path, subtract_neuropil=True, neuropil_coeff=0.7):
    found_stat = False

    for root, dirs, files in os.walk(s2p_path):

        for file in files:

            if file == 'F.npy':
                all_cells = np.load(os.path.join(root, file), allow_pickle=True)
            elif file == 'Fneu.npy':
                neuropil = np.load(os.path.join(root, file), allow_pickle=True)
            elif file == 'iscell.npy':
                is_cells = np.load(os.path.join(root, file),
                                   allow_pickle=True)[:, 0]
                is_cells = np.ndarray.astype(is_cells, 'bool')
                print('Loading {} traces labelled as cells'
                      .format(sum(is_cells)))
            elif file == 'spks.npy':
                spks = np.load(os.path.join(root, file), allow_pickle=True)
            elif file == 'stat.npy':
                stat = np.load(os.path.join(root, file), allow_pickle=True)
                found_stat = True

    if not found_stat:
        raise FileNotFoundError('Could not find stat, '
                                'this is likely not a suit2p folder, s2pResultsPath: ', s2p_path)
    for i, s in enumerate(stat):
        s['original_index'] = i

    all_cells = all_cells[is_cells, :]
    neuropil = neuropil[is_cells, :]
    spks = spks[is_cells, :]
    stat = stat[is_cells]

    if not subtract_neuropil:
        return all_cells, spks, stat, neuropil

    else:
        print('Subtracting neuropil with a coefficient of {}'
              .format(neuropil_coeff))
        neuropil_corrected = all_cells - neuropil * neuropil_coeff
        return neuropil_corrected, spks, stat, neuropil


def correct_s2p_combined(s2p_path, n_planes):
    len_count = 0
    for i in range(n_planes):

        iscell = np.load(os.path.join(s2p_path, 'plane{}'.format(i),
                                      'iscell.npy'), allow_pickle=True)

        if i == 0:
            allcells = iscell
        else:
            allcells = np.vstack((allcells, iscell))

        len_count += len(iscell)

    combined_iscell = os.path.join(s2p_path, 'combined', 'iscell.npy')

    ic = np.load(combined_iscell, allow_pickle=True)
    assert ic.shape == allcells.shape
    assert len_count == len(ic)

    np.save(combined_iscell, allcells)


def read_fiji(csv_path):
    '''reads the csv file saved through plot z axis profile in fiji'''

    data = []

    with open(csv_path, 'r') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        for i, row in enumerate(spamreader):
            if i == 0:
                continue
            data.append(float(row[0].split(',')[1]))

    return np.array(data)


def save_fiji(arr):
    '''saves numpy array in current folder as fiji friendly tiff'''
    tf.imsave('Vape_array.tiff', arr.astype('int16'))


def threshold_detect(signal, threshold):
    '''lloyd russell'''
    thresh_signal = signal > threshold
    thresh_signal[1:][thresh_signal[:-1] & thresh_signal[1:]] = False
    times = np.where(thresh_signal)
    return times[0]


def pade_approx_norminv(p):
    q = math.sqrt(2 * math.pi) * (p - 1 / 2) - (157 / 231) * math.sqrt(2) * \
        math.pi ** (3 / 2) * (p - 1 / 2) ** 3
    r = 1 - (78 / 77) * math.pi * (p - 1 / 2) ** 2 + (241 * math.pi ** 2 / 2310) * \
        (p - 1 / 2) ** 4
    return q / r


def d_prime(hit_rate, false_alarm_rate):
    return pade_approx_norminv(hit_rate) - \
           pade_approx_norminv(false_alarm_rate)


def paq_data(paq, chan_name, threshold_ttl=False, plot=False):
    '''
    returns the data in paq (from paq_read) from channel: chan_names
    if threshold_tll: returns sample that trigger occured on
    '''

    chan_idx = paq['chan_names'].index(chan_name)
    data = paq['data'][chan_idx, :]
    if threshold_ttl:
        data = threshold_detect(data, 1)

    if plot:
        if threshold_ttl:
            plt.plot(data, np.ones(len(data)), '.')
        else:
            plt.plot(data)

    return data


def stim_start_frame_mat(stim_times, frames_ms, fs=5, debug_print=False):
    ''' function to replace stim_start_frames
        Inputs:
        stim_times -- times that stim occured (same reference frame
                      as frames_ms
        frames_ms -- matrix of cell frame times [num_cells x num_frames]
        fs -- frame rate of the imaging for an inidividual plane (frames/second)
        debug_print -- whether to print useful debugging statment about each
                       stim and associated frame time
        Returns:
        stim_idxs -- matrix of frame indexes that stim occured on for each cell
                     [num_trials x num_cells]

        '''

    # The substituion with -1 causes an inplace mutation of the start_times
    # variable in the run objects, copy to avoid this
    stim_times_copy = copy.deepcopy(stim_times)

    # get rid of stims that occur outside the frame clock
    max_frame = np.nanmax(frames_ms)
    min_frame = np.nanmin(frames_ms)
    keep_idx = np.repeat(False, len(stim_times_copy))
    keep_idx[np.where((stim_times_copy < max_frame) & (
            stim_times_copy > min_frame))[0]] = True
    stim_times_copy[~keep_idx] = -1

    ifi_ms = 1 / fs * 1000  # inter-frame-interval in ms
    arg_sorted = np.argsort(frames_ms, axis=1)
    n_cells = frames_ms.shape[0]

    for i, stim_time in enumerate(stim_times_copy):

        def closest_finder(arr, sorter):
            return np.searchsorted(
                arr, stim_time, sorter=sorter)

        arg_idx = [closest_finder(frames_ms[i, :], arg_sorted[i, :])
                   for i in range(n_cells)]
        stim_idx = arg_sorted[np.arange(len(arg_idx)), arg_idx]

        # times of the indexes
        vals = frames_ms[np.arange(len(stim_idx)), stim_idx]

        # if the closest frame is after the stim, move one back
        ahead_idx = np.where(vals > stim_time)[0]
        stim_idx[ahead_idx] = stim_idx[ahead_idx] - 1
        # times of the indexes
        vals = frames_ms[np.arange(len(stim_idx)), stim_idx]

        # if there are nans in the frames_ms row then this stim was likely
        # not imaged. If the stim is > inter-frame_interval from a
        # frame then discount this stim (currently only checking this
        # on the first cell
        if np.isnan(vals).any() or abs(stim_time - vals[0]) > ifi_ms or \
                stim_time == -1:
            stim_idx = np.full(stim_idx.shape, np.nan)
        else:
            if debug_print:
                print('\nval is {}'.format(vals[0]))
                print('stim_time is {}'.format(stim_time))
                print('stim_idx is {}'.format(max(stim_idx)))

            vals2 = frames_ms[range(len(stim_idx)), stim_idx]

            if debug_print:
                print('val2 is {}'.format(vals2[0]))

        if i == 0:
            stim_idxs = stim_idx
        else:
            stim_idxs = np.vstack((stim_idxs, stim_idx))

    return np.transpose(stim_idxs)


def stim_start_frame(paq=None, stim_chan_name=None, frame_clock=None,
                     stim_times=None):
    '''Returns the frames from a frame_clock that a stim occured on.
       Either give paq and stim_chan_name as arugments if using
       unprocessed paq.
       Or predigitised frame_clock and stim_times in reference frame
       of that clock

    '''

    if frame_clock is None:
        frame_clock = paq_data(paq, 'frame_clock', threshold_ttl=True)
        stim_times = paq_data(paq, stim_chan_name, threshold_ttl=True)

    stim_times = [stim for stim in stim_times if stim < np.nanmax(frame_clock)]

    frames = []

    for stim in stim_times:
        # the sample time of the frame immediately preceeding stim
        frame = next(frame_clock[i - 1] for i, sample in enumerate(frame_clock)
                     if sample - stim > 0)
        frames.append(frame)

    return np.array(frames)


def myround(x, base=5):
    '''allow rounding to nearest base number for
       use with multiplane stack slicing'''

    return base * round(x / base)


def tseries_finder(tseries_lens, frame_clock, paq_rate=20000):
    ''' Finds chunks of frame clock that correspond to the tseries in
        tseries lens
        tseries_lens -- ls of the number of frames each tseries you want
                        to find contains
        frame_clock  -- thresholded times each frame recorded in paqio occured
        paq_rate     -- input sampling rate of paqio

        '''

    # frame clock recorded in paqio, includes TTLs from cliking 'live'
    # and foxy extras
    clock = frame_clock / paq_rate

    # break the recorded frame clock up into individual aquisitions
    # where TTLs are seperated by more than 1s
    gap_idx = np.where(np.diff(clock) > 1)
    gap_idx = np.insert(gap_idx, 0, 0)
    gap_idx = np.append(gap_idx, len(clock))
    chunked_paqio = np.diff(gap_idx)

    # are each of the frames recorded by the frame clock actually
    # in processed tseries?
    real_frames = np.zeros(len(clock))
    # the max number of extra frames foxy could spit out
    foxy_limit = 20
    # the number of tseries blocks that have already been found
    series_found = 0
    # count how many frames have been labelled as real or not
    counter = 0

    for chunk in chunked_paqio:
        is_tseries = False

        # iterate through the actual length of each analysed tseries
        for idx, ts in enumerate(tseries_lens):
            # ignore previously found tseries
            if idx < series_found:
                continue

            # the frame clock block matches the number of frames in a tseries
            if chunk >= ts and chunk <= ts + foxy_limit:
                # this chunk of paqio clock is a recorded tseries
                is_tseries = True
                # advance the number of tseries found so they are not
                # detected twice
                series_found += 1
                break

        if is_tseries:
            # foxy bonus frames
            extra_frames = chunk - ts
            # mark tseries frames as real
            real_frames[counter:counter + ts] = 1
            # move the counter on by the length of the real tseries
            counter += ts
            # set foxy bonus frames to not real
            real_frames[counter:counter + extra_frames] = 0
            # move the counter along by the number of foxy bonus frames
            counter += extra_frames

        else:
            # not a tseries so just move the counter along by the chunk
            # of paqio clock
            # this could be wrong, not sure if i've fixed the ob1 error,
            # go careful
            counter += chunk + 1

    real_idx = np.where(real_frames == 1)

    return frame_clock[real_idx]


def flu_splitter(flu, clock, t_starts, pre_frames, post_frames):
    '''Split a fluoresence matrix into trial by trial array

       flu -- fluoresence matrix [num_cells x num_frames]
       clock -- the time that each frame occured
       t_starts -- the time each frame started
       pre_frames -- the number of frames before t_start
                     to include in the trial
       post_frames --  the number of frames after t_start
                       to include in the trial

       returns
       trial_flu -- trial by trial array
                    [num_cells x trial frames x num_trials]
       imaging_trial -- ls of booleans of len num_trials,
                        was the trial imaged?

       n.b. clock and t_start must have same units and
            reference frame (see rsync_aligner.py

       '''

    assert flu.shape[1] == len(clock), '{} frames in fluorescent array ' \
                                       '{} frames in clock' \
        .format(flu.shape[1], len(clock))

    num_trials = len(t_starts)
    imaging_trial = [False] * num_trials  # was the trial imaged?

    first = True  # dumb way of building array in for loop
    for trial, t_start in enumerate(t_starts):
        # the trial occured before imaging started
        if t_start < min(clock):
            continue

        # find the first frame occuring after each trial start
        for idx, frame in enumerate(clock):
            # the idx the frame immediiately proceeds the t_start
            if frame - t_start >= 0:

                imaging_trial[trial] = True
                flu_chunk = flu[:, idx - pre_frames:idx + post_frames]

                if first:
                    trial_flu = flu_chunk
                    first = False
                else:
                    trial_flu = np.dstack((trial_flu, flu_chunk))
                break

    assert trial_flu.shape[2] == sum(imaging_trial)

    return trial_flu, imaging_trial


def flu_splitter2(flu, stim_times, frames_ms, pre_frames=10, post_frames=30):
    stim_idxs = stim_start_frame_mat(stim_times, frames_ms, debug_print=False)

    stim_idxs = stim_idxs[:, np.where((stim_idxs[0, :] - pre_frames > 0) &
                                      (stim_idxs[0, :] + post_frames
                                       < flu.shape[1]))[0]]

    n_trials = stim_idxs.shape[1]
    n_cells = frames_ms.shape[0]

    for i, shift in enumerate(np.arange(-pre_frames, post_frames)):
        if i == 0:
            trial_idx = stim_idxs + shift
        else:
            trial_idx = np.dstack((trial_idx, stim_idxs + shift))

    tot_frames = pre_frames + post_frames
    trial_idx = trial_idx.reshape((n_cells, n_trials * tot_frames))

    flu_trials = []
    for i, idxs in enumerate(trial_idx):
        idxs = idxs[~np.isnan(idxs)].astype('int')
        flu_trials.append(flu[i, idxs])

    n_trials_valid = len(idxs)
    flu_trials = np.array(flu_trials).reshape(
        (n_cells, int(n_trials_valid / tot_frames), tot_frames))

    return flu_trials


def flu_splitter3(flu, stim_times, frames_ms, pre_frames=10, post_frames=30):
    stim_idxs = stim_start_frame_mat(stim_times, frames_ms, debug_print=False)

    # not 100% sure about this line, keep an eye
    stim_idxs[:, np.where((stim_idxs[0, :] - pre_frames <= 0) |
                          (stim_idxs[0, :] + post_frames
                           >= flu.shape[1]))[0]] = np.nan

    n_trials = stim_idxs.shape[1]
    n_cells = frames_ms.shape[0]

    for i, shift in enumerate(np.arange(-pre_frames, post_frames)):
        if i == 0:
            trial_idx = stim_idxs + shift
        else:
            trial_idx = np.dstack((trial_idx, stim_idxs + shift))

    tot_frames = pre_frames + post_frames
    trial_idx = trial_idx.reshape((n_cells, n_trials * tot_frames))

    # flu_trials = np.repeat(np.nan, n_cells*n_trials*tot_frames)
    # flu_trials = np.reshape(flu_trials, (n_cells, n_trials, tot_frames))
    flu_trials = np.full_like(trial_idx, np.nan)
    # iterate through each cell and add trial frames
    for i, idxs in enumerate(trial_idx):
        non_nan = ~np.isnan(idxs)
        idxs = idxs[~np.isnan(idxs)].astype('int')
        flu_trials[i, non_nan] = flu[i, idxs]

    flu_trials = np.reshape(flu_trials, (n_cells, n_trials, tot_frames))
    return flu_trials


def closest_frame_before(clock, t):
    ''' returns the idx of the frame immediately preceeding
        the time t. Frame clock must be digitised and expressed
        in the same reference frame as t
        '''
    subbed = np.array(clock) - t
    return np.where(subbed < 0, subbed, -np.inf).argmax()


def closest_frame(clock, t):
    ''' Returns the idx of the frame closest to  
        the time t. 
        Frame clock must be digitised and expressed
        in the same reference frame as t.
        '''
    subbed = np.array(clock) - t
    return np.argmin(abs(subbed))


def test_responsive(flu, frame_clock, stim_times, pre_frames=10,
                    post_frames=10, offset=0):
    ''' Tests if cells in a fluoresence array are significantly responsive
        to a stimulus

        Inputs:
        flu -- fluoresence matrix [n_cells x n_frames] likely dfof from suite2p
        frame_clock -- timing of the frames, must be digitised and in same
                       reference frame as stim_times
        stim_times -- times that stims to test responsiveness on occured,
                      must be digitised and in same reference frame
                      as frame_clock
        pre_frames -- the number of frames before the stimulus occured to
                      baseline with
        post_frames -- the number of frames after stimulus to test differnece
                       compared
                       to baseline
        offset -- the number of frames to offset post_frames from the
                  stimulus, so don't take into account e.g. stimulus artifact

        Returns:
        pre -- matrix of fluorescence values in the pre_frames period
               [n_cells x n_frames]
        post -- matrix of fluorescence values in the post_frames period
                [n_cells x n_frames]
        pvals -- vector of pvalues from the significance test [n_cells]

        '''

    n_frames = flu.shape[1]

    pre_idx = np.repeat(False, n_frames)
    post_idx = np.repeat(False, n_frames)

    # keep track of the previous stim frame to warn against overlap
    prev_frame = 0

    for i, stim_time in enumerate(stim_times):

        stim_frame = closest_frame_before(frame_clock, stim_time)

        if stim_frame - pre_frames <= 0 or stim_frame + post_frames + offset \
                >= n_frames:
            continue
        elif stim_frame - pre_frames <= prev_frame:
            print('WARNING: STA for stim number {} overlaps with the '
                  'previous stim pre and post arrays can not be '
                  'reshaped to trial by trial'.format(i))

        prev_frame = stim_frame

        pre_idx[stim_frame - pre_frames: stim_frame] = True
        post_idx[stim_frame + offset: stim_frame + post_frames + offset] = True

    pre = flu[:, pre_idx]
    post = flu[:, post_idx]

    _, pvals = stats.ttest_ind(pre, post, axis=1)

    return pre, post, pvals


def build_flu_array(run, stim_times, pre_frames=10, post_frames=50,
                    use_spks=False, is_prereward=False):
    ''' converts [n_cells x n_frames] matrix to trial by trial array
        [n_cells x n_trials x pre_frames+post_frames]

        Inputs:
        run -- BlimpImport object with attributes flu and frames_ms
        stim_times -- times of trial start stims, should be same
                      reference frame as frames_ms
        pre_frames -- number of frames before stim to include in
                      trial
        post_frames -- number of frames after stim to include
                       in trial

        Returns:
        flu_array -- array [n_cells x n_trials x pre_frames+post_frames]

    '''

    if use_spks:
        flu = run.spks
    else:
        flu = run.flu

    if is_prereward:
        frames_ms = run.frames_ms_pre
    else:
        frames_ms = run.frames_ms

    # split flu matrix into trials based on stim time
    flu_array = flu_splitter3(flu, stim_times, frames_ms,
                              pre_frames=pre_frames, post_frames=post_frames)

    return flu_array


def averager(array_list, pre_frames=10, post_frames=50, offset=0,
             trial_filter=None, plot=False, fs=5):
    ''' Averages ls of trial by trial fluoresence arrays and can
        visualise results

        Inputs:
        array_list -- ls of tbt fluoresence arrays
        pre_frames -- number of frames before stim to include in
                      trial
        post_frames -- number of frames after stim to include
                       in trial
        offset -- number of frames to offset post_frames to avoid artifacts
        trial_filter -- ls of trial indexs to include
        plot -- whether to plot result
        fs -- frame rate / plane

        Returns:
        session_average -- mean array [n_sessions x pre_frames+post_frames]
        scaled_average -- same as session average but all traces start
                          at dfof = 0
        grand_average -- average across all sessions [pre_frames + post_frames]
        cell_average -- ls with length n_sessions contains arrays
                        [n_cells x pre_frames+post_frames]

        '''

    if trial_filter:
        assert len(trial_filter) == len(array_list)
        array_list = [arr[:, filt, :]
                      for arr, filt in zip(array_list, trial_filter)]

    n_sessions = len(array_list)

    cell_average = [np.nanmean(k, 1) for k in array_list]

    session_average = np.array([np.nanmean(np.nanmean(k, 0), 0)
                                for k in array_list])

    scaled_average = np.array([session_average[i, :] - session_average[i, 0]
                               for i in range(n_sessions)])

    grand_average = np.nanmean(scaled_average, 0)

    if plot:
        x_axis = range(len(grand_average))
        plt.plot(x_axis, grand_average)
        plt.plot(x_axis[0:pre_frames],
                 grand_average[0:pre_frames], color='red')
        plt.plot(x_axis[pre_frames + offset:pre_frames + offset
                                            + (post_frames - offset)], grand_average[pre_frames + offset:
                                                                                     pre_frames + offset + (
                                                                                                 post_frames - offset)],
                 color='red')
        for s in scaled_average:
            plt.plot(x_axis, s, alpha=0.2, color='grey')

        plt.ylabel(r'$\Delta $F/F')
        plt.xlabel('Time (Seconds)')
        plt.axvline(x=pre_frames - 1, ls='--', color='red')

    return session_average, scaled_average, grand_average, cell_average


def lick_binner(run):
    ''' makes new easytest binned lick variable in run object '''

    licks = run.session.times.get('lick_1')

    binned_licks = []

    for i, t_start in enumerate(run.trial_start):
        if i == len(run.trial_start) - 1:
            t_end = np.inf
        else:
            t_end = run.trial_start[i + 1]

        trial_idx = np.where((licks >= t_start) & (licks <= t_end))[0]

        trial_licks = licks[trial_idx] - t_start

        binned_licks.append(trial_licks)

    run.licks = licks
    # attribute already exists called 'binned_licks' and cannot overwrite it
    run.binned_licks_easytest = binned_licks

    return run


def prepost_diff(array_list, pre_frames=10,
                 post_frames=50, offset=0, filter_list=None):
    n_sessions = len(array_list)

    if filter_list:
        array_list = [array_list[i][:, filter_list[i], :]
                      for i in range(n_sessions)]

    session_average, _, _, cell_average = averager(
        array_list, pre_frames, post_frames)

    post = np.nanmean(
        session_average[:, pre_frames + offset:pre_frames + offset
                                               + (post_frames - offset)], 1
    )
    pre = np.nanmean(session_average[:, 0:pre_frames], 1)

    return post - pre


def raster_plot(arr, y_pos=1, color=np.random.rand(3, ), alpha=1,
                marker='.', markersize=12, label=None):
    plt.plot(arr, np.ones(len(arr)) * y_pos, marker,
             color=color, alpha=alpha, markersize=markersize,
             label=label)

def get_spiral_start(x_galvo, debounce_time):
    
    """ Get the sample at which the first spiral in a trial began 
    
    Experimental function involving lots of magic numbers
    to detect spiral onsets.
    Failures should be caught by assertion at end
    Inputs:
    x_galvo -- x_galvo signal recorded in paqio
    debouce_time -- length of time (samples) encapulsating a whole trial
                    ensures only spiral at start of trial is captured
    
    """
    #x_galvo = np.round(x_galvo, 2)
    x_galvo = my_floor(x_galvo, 2)
    
    # Threshold above which to determine signal as onset of square pulse
    square_thresh = 0.02
    # Threshold above which to consider signal a spiral (empirically determined)
    diff_thresh = 10
    
    # remove noise from parked galvo signal
    x_galvo[x_galvo < -0.5] = -0.6
    
    diffed = np.diff(x_galvo)
    # remove the onset of galvo movement from f' signal
    diffed[diffed > square_thresh] = 0
    diffed = non_zero_smoother(diffed, window_size=200)
    diffed[diffed>30] = 0
    
    # detect onset of sprials
    spiral_start = threshold_detect(diffed, diff_thresh)
    
    if len(spiral_start) == 0:
        print('No spirals found')
        return None
    else:
        # Debounce to remove spirals that are not the onset of the trial
        spiral_start = spiral_start[np.hstack((np.inf, np.diff(spiral_start))) > debounce_time]
        n_squares = len(threshold_detect(x_galvo, -0.5))
        assert len(spiral_start) == n_squares, \
        'spiral_start has len {} but there are {} square pulses'.format(len(spiral_start), n_squares)
        return spiral_start


def non_zero_smoother(arr, window_size=200):
    
    """ Smooths an array by changing values to the number of
        non-0 elements with window
        
        """
    
    windows = np.arange(0, len(arr), window_size)
    windows = np.append(windows, len(arr))

    for idx in range(len(windows)):

        chunk_start = windows[idx]
        
        if idx == len(windows) - 1:
            chunk_end = len(arr)
        else:
            chunk_end = windows[idx+1]
            
        arr[chunk_start:chunk_end] = np.count_nonzero(arr[chunk_start:chunk_end])
    
    return arr


def my_floor(a, precision=0):
    # Floors to a specified number of dps
    return np.round(a - 0.5 * 10**(-precision), precision)


def get_trial_frames(clock, start, pre_frames, post_frames, paq_rate, fs=30):

    # The frames immediately preceeding stim
    start_idx = closest_frame_before(clock, start)
    frames = np.arange(start_idx-pre_frames, start_idx+post_frames)
    
    # Is the trial outside of the frame clock
    is_beyond_clock = np.max(frames) >= len(clock) or np.min(frames) < 0
    
    if is_beyond_clock:
        return None, None
    
    frame_to_start = (start - clock[start_idx]) / paq_rate  # time (s) from frame to trial_start
    frame_time_diff = np.diff(clock[frames]) / paq_rate  # ifi (s)
    
    # did the function find the correct frame
    is_not_correct_frame = clock[start_idx+1]  < start or clock[start_idx] > start
    # the nearest frame to trial start was not during trial
    # if the time to the nearest frame is less than upper bound of inter-frame-interval
    trial_not_running = frame_to_start > 1/(fs-1)
    frames_not_consecutive = np.max(frame_time_diff) > 1/(fs-1)
    
    if trial_not_running or frames_not_consecutive:
        return None, None
    
    return frames, start_idx


def between_two_hits(idxs, easy_idxs, easy_outcome):
    
    assert len(easy_idxs) == len(easy_outcome)
    
    # Next easy trial from each test trial
    closest_after = np.array([bisect.bisect_left(easy_idxs, idx) for idx in idxs])
    # Previous easy trial from each test trial
    closest_before = closest_after - 1
    # Test trials before the first easy trial should have both previous and next
    # as the first easy trial
    closest_before[closest_before==-1] = 0
    # Test trials after the last easy trial should have both previous and next
    # as the last easy trial
    closest_after[idxs>easy_idxs[-1]] = len(easy_idxs)-1
    
    assert len(idxs) == len(closest_before) == len(closest_after)
    
    between_two = []
    for before, after in zip(closest_before, closest_after):
        if easy_outcome[before] and easy_outcome[after] == 'hit':
            between_two.append(True)
        else:
            between_two.append(False)
    
    assert len(between_two) == len(idxs)
    
    return between_two


def points_in_circle_np(radius, x0=0, y0=0, ):
    x_ = np.arange(x0 - radius - 1, x0 + radius + 1, dtype=int)
    y_ = np.arange(y0 - radius - 1, y0 + radius + 1, dtype=int)
    x, y = np.where((x_[:,np.newaxis] - x0)**2 + (y_ - y0)**2 <= radius**2)
    for x, y in zip(x_[x], y_[y]):
        yield x, y
