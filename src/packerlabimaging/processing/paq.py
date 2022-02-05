from typing import List

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.ticker as mticker
import matplotlib.pyplot as plt
from scipy import io

from packerlabimaging.utils.utils import threshold_detect

def paq2py(file_path=None, plot=False):
    """
    Read PAQ file (from PackIO) into python
    Lloyd Russell 2015. Minor update for numpy >1.18 by Prajay Shah 2021.
    Parameters
    ==========
    file_path : str, optional
        full path to file to read in. if none is supplied a load file dialog
        is opened, buggy on mac osx - Tk/matplotlib. Default: None.
    plot : bool, optional
        plot the data after reading? Default: False.
    Returns
    =======
    data : ndarray
        the data as a m-by-n array where m is the number of channels and n is
        the number of datapoints
    chan_names : list of str
        the names of the channels provided in PackIO
    hw_chans : list of str
        the hardware lines corresponding to each channel
    units : list of str
        the units of measurement for each channel
    rate : int
        the acquisition sample rate, in Hz
    """

    # file load gui
    if file_path is None:
        import Tkinter
        import tkFileDialog
        root = Tkinter.Tk()
        root.withdraw()
        file_path = tkFileDialog.askopenfilename()
        root.destroy()

    # open file
    fid = open(file_path, 'rb')

    # get sample rate
    rate = int(np.fromfile(fid, dtype='>f', count=1))

    # get number of channels
    num_chans = int(np.fromfile(fid, dtype='>f', count=1))

    # get channel names
    chan_names = []
    for i in range(num_chans):
        num_chars = int(np.fromfile(fid, dtype='>f', count=1))
        chan_name = ''
        for j in range(num_chars):
            chan_name = chan_name + chr(np.fromfile(fid, dtype='>f', count=1)[0])
        chan_names.append(chan_name)

    # get channel hardware lines
    hw_chans = []
    for i in range(num_chans):
        num_chars = int(np.fromfile(fid, dtype='>f', count=1))
        hw_chan = ''
        for j in range(num_chars):
            hw_chan = hw_chan + chr(np.fromfile(fid, dtype='>f', count=1)[0])
        hw_chans.append(hw_chan)

    # get acquisition units
    units = []
    for i in range(num_chans):
        num_chars = int(np.fromfile(fid, dtype='>f', count=1))
        unit = ''
        for j in range(num_chars):
            unit = unit + chr(np.fromfile(fid, dtype='>f', count=1)[0])
        units.append(unit)

    # get data
    temp_data = np.fromfile(fid, dtype='>f', count=-1)
    num_datapoints = int(len(temp_data) / num_chans)
    data = np.reshape(temp_data, [num_datapoints, num_chans]).transpose()

    # close file
    fid.close()

    # plot
    if plot:
        # import matplotlib
        # matplotlib.use('QT4Agg')
        import matplotlib.pylab as plt
        f, axes = plt.subplots(num_chans, 1, sharex=True, figsize=(15, num_chans*5), frameon=False)
        for idx, ax in enumerate(axes):
            ax.plot(data[idx])
            ax.set_xlim([0, num_datapoints - 1])
            ax.set_ylim([data[idx].min() - 1, data[idx].max() + 1])
            # ax.set_ylabel(units[idx])
            ax.set_title(chan_names[idx])

            # -- Prajay edit
            # change x axis ticks to seconds
            label_format = '{:,.0f}'
            labels = [item for item in ax.get_xticks()]
            for item in labels:
                labels[labels.index(item)] = int(round(item / rate))
            ticks_loc = ax.get_xticks().tolist()
            ax.xaxis.set_major_locator(mticker.FixedLocator(ticks_loc))
            ax.set_xticklabels([label_format.format(x) for x in labels])
            ax.set_xlabel('Time (secs)')
            # --

        plt.suptitle(file_path)
        plt.tight_layout()
        plt.show()

    # make pandas data frame using data in channels
    df = pd.DataFrame(data.T, columns=chan_names)

    return {"data": data,
            "chan_names": chan_names,
            "hw_chans": hw_chans,
            "units": units,
            "rate": rate,
            "num_datapoints": num_datapoints}, df


class paqData:
    def __init__(self, paq_path: str, option: List[str]):
        """
        reads in paq data from a .paq file for an experiment performed using PackIO.

        paq_path: full path to .paq file to read
        """
        self.frame_times = None
        self.paq_path = paq_path     # full path to the .paq file to process
        self.paq_channels: List[str] = ['None']     # recorded channels in paq file
        self.paq_rate: float = 0.0                  # sample rate of paq collection
        self.sparse_paq_data = {}  # contains data from all paq channels decimated to frame clock times


        paq_data, self.paq_rate, self.paq_channels = self.paq_read(paq_path=self.paq_path)
        self.paqProcessing(paq=paq_data, options=option)

    def __repr__(self):
        information = ""
        for i in self.__dict__:
            information += f"\n\t{i}: {self.__dict__[i]}"

        return f"packerlabimaging.processing.paq.paqData: {information}"

    @staticmethod
    def paq_read(paq_path: str = None, plot: bool = False):
        """
        Loads .paq file and saves data from individual channels.

        :param paq_path: (optional) path to the .paq file for this data object
        """

        print(f'\tloading paq data from: {paq_path}')
        paq, _ = paq2py(paq_path, plot=plot)
        paq_rate = paq['rate']
        paq_channels = paq['chan_names']
        print(f"\t|- loaded {len(paq['chan_names'])} channels from .paq file: {paq['chan_names']}")

        return paq, paq_rate, paq_channels

    def storePaqChannel(self, chan_name):
        """add a specific channel's (`chan_name`) data from the .paq file as attribute of the same name for
        paqData object."""

        paq_data, _, paq_channels = self.paq_read(paq_path=self.paq_path)
        print(paq_channels)
        chan_name_idx = paq_channels.index(chan_name)
        setattr(self, chan_name, paq_data['data'][chan_name_idx])

    def paqProcessing(self, paq, options: List[str]):  # TODO is this best implementation of this??
        """
        Loads .paq file and saves data from individual channels.

        :param paq_path: (optional) path to the .paq file for this data object
        """

        print('\n\----- Processing paq file ...')
        # retrieve frame times
        if 'TwoPhotonImaging' or 'AllOptical' in options:
            self.frame_times = self._frame_times(paq_data=paq)
            # read in and save sparse version of all paq channels (only save data from timepoints at frame clock times)
            for idx, chan in enumerate(self.paq_channels):
                self.sparse_paq_data[chan] = paq['data'][idx, self.frame_times]

        elif 'OnePhotonStim' in options:
            self._1p_stims(paq_data=paq)



    @staticmethod
    def _frame_times(paq_data, frame_channel: str = 'frame_clock'):
        if frame_channel not in paq_data['chan_names']:
            raise KeyError(f'{frame_channel} not found in .paq channels. Specify channel containing frame signals.')
        
        # find frame times
        clock_idx = paq_data['chan_names'].index(frame_channel)
        clock_voltage = paq_data['data'][clock_idx, :]

        __frame_clock = threshold_detect(clock_voltage, 1)
        __frame_clock = __frame_clock

        # find start and stop __frame_clock times -- there might be multiple 2p imaging starts/stops in the paq trial (hence multiple frame start and end times)
        frame_start_times = [__frame_clock[0]]  # initialize list
        frame_end_times = []
        i = len(frame_start_times)
        for idx in range(1, len(__frame_clock) - 1):
            if (__frame_clock[idx + 1] - __frame_clock[idx]) > 2e3:
                i += 1
                frame_end_times.append(__frame_clock[idx])
                frame_start_times.append(__frame_clock[idx + 1])
        frame_end_times.append(__frame_clock[-1])

        # handling cases where 2p imaging clock has been started/stopped >1 in the paq trial
        if len(frame_start_times) > 1:
            diff = [frame_end_times[idx] - frame_start_times[idx] for idx in
                    range(len(frame_start_times))]
            idx = diff.index(max(diff))
            frame_start_time_actual = frame_start_times[idx]
            frame_end_time_actual = frame_end_times[idx]
            __frame_clock_actual = [frame for frame in __frame_clock if
                                         frame_start_time_actual <= frame <= frame_end_time_actual]
        else:
            frame_start_time_actual = frame_start_times[0]
            frame_end_time_actual = frame_end_times[0]
            __frame_clock_actual = __frame_clock
        
        return __frame_clock_actual 

    @staticmethod
    def sparse_paq(paq_data, frame_clock):
        # read in and save sparse version of all paq channels (only save data from timepoints at frame clock times)
        sparse_paq_data = {}
        for idx, chan in enumerate(paq_data['chan_names']):
            sparse_paq_data[chan] = paq_data['data'][idx, frame_clock]


    @staticmethod
    def _2p_stims(paq_data, frame_clock: List[int], plot: bool = False, stim_channel: str = ''):
        if stim_channel not in paq_data['chan_names']:
            raise KeyError(f'{stim_channel} not found in .paq channels. Specify channel containing frame signals.')

        # find stim times
        stim_idx = paq_data['chan_names'].index(stim_channel)
        stim_volts = paq_data['data'][stim_idx, :]
        stim_times = threshold_detect(stim_volts, 1)
        # self.stim_times = stim_times
        stim_start_times = stim_times
        print(f'# of stims found on {stim_channel}: {len(stim_start_times)}')

        if plot:
            plt.figure(figsize=(10, 5))
            plt.plot(stim_volts)
            plt.plot(stim_times, np.ones(len(stim_times)), '.')
            plt.suptitle('stim times')
            sns.despine()
            plt.show()

        # TODO need to figure out how to handle multi-plane imaging and retrieving stim frame times
        # find stim frames
        stim_start_frames = []
        for stim in stim_times:
            # the index of the frame immediately preceeding stim
            stim_start_frame = next(
                i - 1 for i, sample in enumerate(frame_clock) if sample - stim >= 0)
            stim_start_frames.append(stim_start_frame)

        return stim_start_frames, stim_start_times

    # TODO review code
    def _1p_stims(self, paq_data, plot: bool = False, optoloopback_channel: str = 'opto_loopback'):
        "find 1p stim times"
        if optoloopback_channel not in paq_data['chan_names']:
            raise KeyError(f'{optoloopback_channel} not found in .paq channels. Specify channel containing 1p stim TTL loopback signals.')

        opto_loopback_chan = paq_data['chan_names'].index('opto_loopback')
        stim_volts = paq_data['data'][opto_loopback_chan, :]
        stim_times = threshold_detect(stim_volts, 1)

        self.stim_times = stim_times
        self.stim_start_times = [self.stim_times[0]]  # initialize ls
        self.stim_end_times = []
        i = len(self.stim_start_times)
        for stim in self.stim_times[1:]:
            if (stim - self.stim_start_times[i - 1]) > 1e5:
                i += 1
                self.stim_start_times.append(stim)
                self.stim_end_times.append(self.stim_times[np.where(self.stim_times == stim)[0] - 1][0])
        self.stim_end_times.append(self.stim_times[-1])

        print("\nNumber of 1photon stims found: ", len(self.stim_start_times))

        if plot:
            plt.figure(figsize=(50, 2))
            plt.plot(stim_volts)
            plt.plot(stim_times, np.ones(len(stim_times)), '.')
            plt.suptitle('1p stims from paq, with detected 1p stim instances as scatter')
            plt.xlim([stim_times[0] - 2e3, stim_times[-1] + 2e3])
            plt.show()
        

        # find all stim frames
        self.stim_frames = []
        for stim in range(len(self.stim_start_times)):
            stim_frames_ = [frame for frame, t in enumerate(self._frame_clock_actual) if
                            self.stim_start_times[stim] - 100 / self.paq_rate <= t <= self.stim_end_times[
                                stim] + 100 / self.paq_rate]

            self.stim_frames.append(stim_frames_)

        # if >1 1p stims per trial, find the start of all 1p trials
        self.stim_start_frames = [stim_frames[0] for stim_frames in self.stim_frames if len(stim_frames) > 0]
        self.stim_end_frames = [stim_frames[-1] for stim_frames in self.stim_frames if len(stim_frames) > 0]
        self.stim_duration_frames = int(np.mean(
            [self.stim_end_frames[idx] - self.stim_start_frames[idx] for idx in range(len(self.stim_start_frames))]))

        print(f"\nStim duration of 1photon stim: {self.stim_duration_frames} frames")


    def _shutter_times(self, paq_data, shutter_channel: str = 'shutter_loopback'):
        "find shutter loopback frames from .paq data"

        if shutter_channel not in paq_data['chan_names']:
            raise KeyError(f'{shutter_channel} not found in .paq channels. Specify channel containing shutter signals.')

        shutter_idx = paq_data['chan_names'].index('shutter_loopback')
        shutter_voltage = paq_data['data'][shutter_idx, :]

        shutter_times = np.where(shutter_voltage > 4)
        self.shutter_times = shutter_times[0]
        self.shutter_frames = []
        self.shutter_start_frames = []
        self.shutter_end_frames = []

        shutter_frames_ = [frame for frame, t in enumerate(self._frame_times()) if
                           t in self.shutter_times]
        self.shutter_frames.append(shutter_frames_)

        shutter_start_frames = [shutter_frames_[0]]
        shutter_end_frames = []
        i = len(shutter_start_frames)
        for frame in shutter_frames_[1:]:
            if (frame - shutter_start_frames[i - 1]) > 5:
                i += 1
                shutter_start_frames.append(frame)
                shutter_end_frames.append(shutter_frames_[shutter_frames_.index(frame) - 1])
        shutter_end_frames.append(shutter_frames_[-1])
        self.shutter_start_frames.append(shutter_start_frames)
        self.shutter_end_frames.append(shutter_end_frames)

    def frames_discard(self, input_array, total_frames, discard_all=False):
        '''
        calculate which 2P imaging frames to discard (or use as bad frames input into suite2p) based on the bad frames
        identified by manually inspecting the paq files in EphysViewer.m
        :param paq: paq file
        :param input_array: .m file path to read that contains the timevalues for signal to remove
        :param total_frames: the number of frames in the TIFF file of the actual 2p imaging recording
        :param discard_all: bool; if True, then add all 2p imaging frames from this paq file as bad frames to discard
        :return: array that contains the indices of bad frames (in format ready to input into suite2p processing)
        '''

        frame_times = self._frame_times()
        frame_times = frame_times[
                      0:total_frames]  # this is necessary as there are more TTL triggers in the paq file than actual frames (which are all at the end)

        all_btwn_paired_frames = []
        paired_frames_first = []
        paired_frames_last = []
        if input_array is not None:
            print('\nadding seizure frames loaded up from: ', input_array)
            measurements = io.loadmat(input_array)
            for set_ in range(len(measurements['PairedMeasures'])):
                # calculate the sample value for begin and end of the set
                begin = int(measurements['PairedMeasures'][set_][3][0][0] * self.paq_rate)
                end = int(measurements['PairedMeasures'][set_][5][0][0] * self.paq_rate)
                frames_ = list(np.where(np.logical_and(frame_times >= begin, frame_times <= end))[0])
                if len(frames_) > 0:
                    all_btwn_paired_frames.append(frames_)
                    paired_frames_first.append(frames_[0])
                    paired_frames_last.append(frames_[-1])

            all_btwn_paired_frames = [item for x in all_btwn_paired_frames for item in x]

        if discard_all and input_array is None:
            frames_to_discard = list(range(len(frame_times)))
            return frames_to_discard
        elif not discard_all and input_array is not None:
            frames_to_discard = all_btwn_paired_frames
            return frames_to_discard, all_btwn_paired_frames, paired_frames_first, paired_frames_last
        elif discard_all and input_array is not None:
            frames_to_discard = list(range(len(frame_times)))
            return frames_to_discard, all_btwn_paired_frames, paired_frames_first, paired_frames_last
        else:
            raise ReferenceError('something wrong....No frames selected for discarding')