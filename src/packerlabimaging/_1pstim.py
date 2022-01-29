## main module for parsing, processing and interacting with data/files of 1p-stim protocols
## - 1pstim module - just copied straight from allopticalseizure version so far..
import numpy as np
from matplotlib import pyplot as plt

from .TwoPhotonImagingMain import TwoPhotonImagingTrial
from ._paq import paqData
from ._utils import threshold_detect


class onePstim(TwoPhotonImagingTrial):

    compatible_responses_process = ['pre-stim dFF', 'post - pre']

    def __init__(self, data_path_base, date, animal_prep, trial, metainfo, analysis_save_path_base: str = None):
        paqs_loc = '%s%s_%s_%s.paq' % (
            data_path_base, date, animal_prep, trial[2:])  # path to the .paq files for the selected trials
        tiffs_loc_dir = '%s/%s_%s' % (data_path_base, date, trial)
        tiffs_loc = '%s/%s_%s_Cycle00001_Ch3.tif' % (tiffs_loc_dir, date, trial)
        self.pkl_path = "/home/pshah/mnt/qnap/Analysis/%s/%s_%s/%s_%s.pkl" % (
            date, date, trial, date, trial)  # specify path in Analysis folder to save pkl object
        # paqs_loc = '%s/%s_RL109_010.paq' % (data_path_base, date)  # path to the .paq files for the selected trials
        new_tiffs = tiffs_loc[:-19]  # where new tiffs from rm_artifacts_tiffs will be saved

        # make the necessary Analysis saving subfolder as well
        if analysis_save_path_base is None:
            analysis_save_path = tiffs_loc[:21] + 'Analysis/' + tiffs_loc_dir[26:]
        else:
            analysis_save_path = analysis_save_path_base + tiffs_loc_dir[-16:]

        print('----------------------------------------')
        print('-----Processing trial # %s-----' % trial)
        print('----------------------------------------\n')

        paths = [tiffs_loc_dir, tiffs_loc, paqs_loc]
        # print('tiffs_loc_dir, naparms_loc, paqs_loc paths:\n', paths)

        self.tiff_path = paths[1]
        self.paq_path = paths[2]
        TwoPhotonImagingTrial.__init__(self, self.tiff_path, self.paq_path, metainfo=metainfo,
                                  analysis_save_path=analysis_save_path, save_downsampled_tiff=True, quick=False)

        # using the paq module for loading paq data
        self.paq_data = paqData(paq_path=self.paq_path)
        self._1p_stims(plot=False, optoloopback_channel='opto_loopback')

        self.paqProcessing()

        # add all frames as bad frames incase want to include this trial in suite2p run
        self.bad_frames = Utils.frames_discard(paq=paqData.paq_read(paq_path=self.paq_path), input_array=None, total_frames=self.n_frames, discard_all=True)

        self.save(pkl_path=self.pkl_path)

        print('\n-----DONE OnePhotonStim init of trial # %s-----' % trial)

    def __repr__(self):
        if os.path.exists(self.pkl_path) and hasattr(self, 'metainfo'):
            lastmod = time.ctime(os.path.getmtime(self.pkl_path))
            prep = self.metainfo['animal prep.']
            trial = self.metainfo['trial']
            information = f"{prep} {trial}, {self.exptype}"
        else:
            information = f"uninitialized"
        return repr(f"({information}) TwoPhotonImaging.OnePhotonStim experimental data object, last saved: {lastmod}")

    @property
    def pre_stim(self):
        return 1  # seconds

    @property
    def post_stim(self):
        return 4  # seconds

    @property
    def response_len(self):
        return 0.5  # post-stim response period in sec

    def _1p_stims(self, plot: bool = False, optoloopback_channel: str = 'opto_loopback'):
        """find 1p stim times

        :param optoloopback_channel: Specify channel containing 1p stim TTL loopback signals.
        :param plot: whether to plot the paq read signal after loading paq file
        """

        if optoloopback_channel not in self.paq_data.paq_channels:
            raise KeyError(
                f'{optoloopback_channel} not found in .paq channels. ')

        opto_loopback_chan = self.paq_data['chan_names'].index(optoloopback_channel)
        
        # load up paq data
        _paq_data, _, _ = paqData.paq_read(paq_path=self.paq_path)
        
        stim_volts = _paq_data['data'][opto_loopback_chan, :]
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

    def _shutter_times(self, shutter_channel: str = 'shutter_loopback'):
        """find shutter loopback frames from .paq data

        :param shutter_channel:  Specify channel containing shutter signals.
        """

        if shutter_channel not in self.paq_data.paq_channels:
            raise KeyError(
                f'{shutter_channel} not found in .paq channels. ')

        shutter_idx = self.paq_data['chan_names'].index(shutter_channel)

        # load up paq data
        _paq_data, _, _ = paqData.paq_read(paq_path=self.paq_path)

        shutter_voltage = _paq_data['data'][shutter_idx, :]

        shutter_times = np.where(shutter_voltage > 4)
        self.shutter_times = shutter_times[0]
        self.shutter_frames = []
        self.shutter_start_frames = []
        self.shutter_end_frames = []

        shutter_frames_ = [frame for frame, t in enumerate(self._frame_clock_actual) if
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