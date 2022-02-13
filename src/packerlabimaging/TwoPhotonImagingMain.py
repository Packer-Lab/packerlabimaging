import os
import time
import datetime
import re
from typing import Optional

import pickle

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import xml.etree.ElementTree as ET
import tifffile as tf

# grabbing functions from .utils_funcs that are used in this script - Prajay's edits (review based on need)
from packerlabimaging.utils.utils import SaveDownsampledTiff, make_tiff_stack, normalize_dff
from packerlabimaging.processing.paq import import_paqdata
from .processing import suite2p, anndata as ad
from .utils.imagingMetadata import PrairieViewMetadata, ImagingMetadata


class TwoPhotonImagingTrial:
    """Just two photon imaging related functions - currently set up for data collected from Bruker microscopes and
    suite2p processed Ca2+ imaging data """

    def __init__(self, metainfo: dict, analysis_save_path: str, microscope: str = 'Bruker', **kwargs):
        """
        TODO update function docstring for approp args
        :param tiff_path: path to t-series .tiff
        :param analysis_save_path: path of where to save the experiment analysis object
        :param microscope: name of microscope used to record imaging (options: "Bruker" (default), "Scientifica", "other")
        :param metainfo: dictionary containing any metainfo information field needed for this experiment. At minimum it needs to include prep #, t-series # and date of data collection.
        :param paq_path: (optional) path to .Paq file associated with current t-series
        :param suite2p_path: (optional) path to suite2p outputs folder associated with this t-series (plane0 file? or ops file? not sure yet)
        :param make_downsampled_tiff: flag to run generation and saving of downsampled tiff of t-series (saves to the analysis save location)
        """

        # Initialize Attributes:

        # # Imaging acquisition attr's: - refactored to _prairieview
        # self.n_frames: int = 0  # number of imaging frames in the current trial
        # self.fps = None  # rate of imaging acquisition (frames per second)
        # self.frame_x = None  # num of pixels in the x direction of a single frame
        # self.frame_y = None  # num of pixels in the y direction of a single frame
        # self.n_planes = None  # num of FOV planes in imaging acquisition
        # self.pix_sz_x = None  # size of a single imaging pixel in x direction (microns)
        # self.pix_sz_y = None  # size of a single imaging pixel in y direction (microns)
        # self.scan_x = None  # TODO ROB - not sure what the comment for this is
        # self.scan_y = None  # TODO ROB - not sure what the comment for this is
        # self.zoom: float = 0.0 # zoom level on Bruker microscope
        # self.last_good_frame = None  # indicates when the last good frame was during the t-series recording, if nothing was wrong the value is 0, otherwise it is >0 and that indicates that PV is not sure what happened after the frame listed, but it could be corrupt data


        if 'date' in [*metainfo] and 'trial' in [*metainfo] and 'animal prep.' in [*metainfo] and 't series id' in [*metainfo] \
                and 'trialsInformation' in [*metainfo]: self.__metainfo = metainfo
        else: raise ValueError("dev error: metainfo argument must contain the minimum fields: 'date', 'trial', 'animal prep.', 't series id', 'trialInformation dict")
        if os.path.exists(metainfo['trialsInformation']['tiff_path']): self.tiff_path = metainfo['trialsInformation']['tiff_path']
        else: raise FileNotFoundError(f"tiff_path does not exist: {metainfo['trialsInformation']['tiff_path']}")
        if 'paq_path' in [*metainfo['trialsInformation']]:
            if os.path.exists(metainfo['trialsInformation']['paq_path']): self.paq_path = metainfo['trialsInformation']['paq_path']
            else: raise FileNotFoundError(f"paq_path does not exist: {metainfo['trialsInformation']['paq_path']}")

        # set and create analysis save path directory
        self.analysis_save_dir = analysis_save_path
        self.__pkl_path = f"{self.analysis_save_dir}{metainfo['date']}_{metainfo['trial']}.pkl"

        self.save_pkl(pkl_path=self.pkl_path)  # save experiment object to pkl_path

        # get imaging setup parameters
        if 'Bruker' in microscope:
            self.imparams = self._getImagingParameters(microscope='Bruker')  # CURRENTLY USING REFACTORED PV METADATA CODE
        elif 'imagingMicroscopeMetadata' in [*kwargs]:
            self.imparams = self._getImagingParameters(metadata=kwargs['imagingMicroscopeMetadata'])
        else:
            Warning(f"NO imaging microscope parameters set. ")

        # self._parsePVMetadata() if 'Bruker' in microscope else Warning(f'retrieving data-collection metainformation from '
        #                                                                f'{microscope} microscope has not been implemented yet')

        # run Paq processing if paq_path is provided for trial
        self.Paq = self._paqProcessingTwoPhotonImaging(paq_path=self.paq_path, frame_channel='frame_clock') if hasattr(self, 'paq_path') else None # TODO set option for specifying frame channel under different name

        # collect mean FOV Trace
        self.meanFluImg, self.meanFovFluTrace  = self.meanRawFluTrace()

        # if provided, add Suite2p results for trial
        for i in ['suite2p_experiment_obj', 'total_frames_stitched']:
            assert i in [*kwargs], f'{i} required in Suite2pResultsTrial call'
            assert kwargs[i] is not None, f'{i} Suite2pResultsTrial call is None'
        if 'suite2p_experiment_obj' in [*kwargs] and 'total_frames_stitched' in [*kwargs]:
            self.Suite2p = suite2p.Suite2pResultsTrial(suite2p_experiment_obj=kwargs['suite2p_experiment_obj'],
                                                        trial_frames=(kwargs['total_frames_stitched'],
                                                                           kwargs['total_frames_stitched'] + self.imparams.n_frames))  # use trial obj's current trial frames

        # normalize dFF for raw Flu
        self.dfof()

        # create annotated data object
        self.data = self.create_anndata()

        ##### SAVE Trial OBJECT
        self.save()
        print(f'\----- CREATING TwoPhotonImagingTrial for trial: {metainfo["trial"]},  {metainfo["t series id"]}')

    def __str__(self):
        if self.pkl_path:
            lastmod = time.ctime(os.path.getmtime(self.pkl_path))
        else:
            lastmod = "(unsaved pkl object)"
        return repr(f"({self.t_series_name}) TwoPhotonImagingTrial experimental data object, last saved: {lastmod}")


    def __repr__(self):
        return repr(f"TwoPhotonImagingTrial experimental data object")

    @property
    def paths(self):
        """TODO returns a dictionary of all paths associated with trial"""
        return None


    @property
    def fig_save_path(self):
        today_date = datetime.today().strftime('%Y-%m-%d')
        return self.analysis_save_dir + f'Results_fig/{today_date}/'

    @fig_save_path.setter
    def fig_save_path(self, value: str):
        "set new default fig save path for data object"
        self.fig_save_path = value

    @property
    def date(self):
        "date of the experiment datacollection"
        return self.__metainfo['date']

    @property
    def prep(self):
        return self.__metainfo['animal prep.']

    @property
    def trial(self):
        return self.__metainfo['trial']

    @property
    def t_series_name(self):
        if 't series id' in self.__metainfo.keys():
            return f"{self.__metainfo['t series id']}"
        elif "animal prep." in self.__metainfo.keys() and "trial" in self.__metainfo.keys():
            return f'{self.__metainfo["animal prep."]} {self.__metainfo["trial"]}'
        else:
            raise ValueError('no information found to retrieve t series id')

    @property
    def tiff_path_dir(self):
        return self.tiff_path[:[(s.start(), s.end()) for s in re.finditer('/', self.tiff_path)][-1][0]]  # this is the directory where the Bruker xml files associated with the 2p imaging TIFF are located

    @property
    def pkl_path(self):
        "path in Analysis folder to save pkl object"
        return self.__pkl_path

    @pkl_path.setter
    def pkl_path(self, path: str):
        self.__pkl_path = path

    def _getImagingParameters(self, metadata: Optional[dict]=None, microscope: Optional[str] = 'Bruker'):
        """retrieves imaging metadata parameters. If using Bruker microscope and PrairieView, then _prairieview module is used to collect this data.

        :param microscope: name of the microscope, currently the only supported microscope for parsing metadata directly is Bruker/PrairieView imaging setup.
        """
        if 'Bruker' in microscope:
            return PrairieViewMetadata(tiff_path_dir=self.tiff_path_dir)
        else:
            try:
                return ImagingMetadata(**metadata)
            except TypeError:
                Exception('required key not present in metadata')

    @property
    def frame_clock(self):
        if hasattr(self.Paq, 'frame_clock'):
            return self.Paq.frame_clock
        else:
            raise ValueError('Frame clock timings couldnt be retrieved from .Paq submodule.')

    @property
    def n_frames(self):
        try:
            return self.imparams.n_frames
        except AttributeError:
            return -1

    def stitch_reg_tiffs(self, first_frame: int, last_frame: int, reg_tif_folder: str = None, force_crop: bool = False,
                         s2p_run_batch: int = 2000):

        """
        Stitches together registered tiffs outputs from suite2p from the provided imaging frame start and end values.

        :param first_frame: first frame from the overall s2p run to start stitching from
        :param last_frame: last frame from the overall s2p run to end stitching at
        :param force_crop:
        :param force_stack:
        :param s2p_run_batch: batch size for suite2p run (defaults to 2000 because that is usually the batch size while running suite2p processing)
        """

        assert hasattr(self,
                       'user_batch_size'), 'No user_batch_size set for Suite2pResultsTrial, please create new attr for .Suite2p.user_batch_size, before continuing'

        if reg_tif_folder is None:
            if self.s2pResultsPath:
                reg_tif_folder = self.s2pResultsPath + '/reg_tif/'
                print(f"\- trying to load registerred tiffs from: {reg_tif_folder}")
        else:
            raise Exception(f"Must provide reg_tif_folder path for loading registered tiffs")
        if not os.path.exists(reg_tif_folder):
            raise Exception(f"no registered tiffs found at path: {reg_tif_folder}")

        first_frame = self.trial_frames[0]
        last_frame = self.trial_frames[-1]
        frame_range = [first_frame, last_frame]

        start = first_frame // s2p_run_batch
        end = last_frame // s2p_run_batch + 1

        # set tiff paths to save registered tiffs:
        tif_path_save = self.analysis_save_dir + 'reg_tiff_%s.tif' % self.metainfo['trial']
        tif_path_save2 = self.analysis_save_dir + 'reg_tiff_%s_r.tif' % self.metainfo['trial']
        reg_tif_list = os.listdir(reg_tif_folder)
        reg_tif_list.sort()
        sorted_paths = [reg_tif_folder + tif for tif in reg_tif_list][start:end + 1]

        print(tif_path_save)
        print(sorted_paths)

        if os.path.exists(tif_path_save):
            make_tiff_stack(sorted_paths, save_as=tif_path_save)

        if not os.path.exists(tif_path_save2) or force_crop:
            with tf.TiffWriter(tif_path_save2, bigtiff=True) as tif:
                with tf.TiffFile(tif_path_save, multifile=False) as input_tif:
                    print('cropping registered tiff')
                    data = input_tif.asarray()
                    print('shape of stitched tiff: ', data.shape)
                reg_tif_crop = data[frame_range[0] - start * s2p_run_batch: frame_range[1] - (
                        frame_range[0] - start * s2p_run_batch)]
                print('saving cropped tiff ', reg_tif_crop.shape)
                tif.save(reg_tif_crop)

    def _paqProcessingTwoPhotonImaging(self, paq_path, frame_channel):
        print(f"\n\- PROCESSING PAQDATA ... ")
        paq_data_obj, paqdata = import_paqdata(paq_path=paq_path)
        paq_data_obj.frame_times_channame = frame_channel
        paq_data_obj.frame_clock = paq_data_obj.paq_frame_times(paq_data=paqdata, frame_channel=frame_channel)
        paq_data_obj.sparse_paq(paq_data=paqdata, frame_clock=paq_data_obj.frame_clock)

        return paq_data_obj

    # refactored to _utils.Utils
    def create_anndata(self):
        """
        Creates annotated data (see anndata library for more information on AnnotatedData) object based around the Ca2+ matrix of the imaging trial.

        """

        if self.Suite2p._s2pResultExists and self.Paq.paq_channels:
            # SETUP THE OBSERVATIONS (CELLS) ANNOTATIONS TO USE IN anndata
            # build dataframe for obs_meta from suite2p stat information
            obs_meta = pd.DataFrame(columns=['original_index', 'footprint', 'mrs', 'mrs0', 'compact', 'med', 'npix', 'radius',
                                             'aspect_ratio', 'npix_norm', 'skew', 'std'], index=range(len(self.Suite2p.stat)))
            for idx, __stat in enumerate(self.Suite2p.stat):
                for __column in obs_meta:
                    obs_meta.loc[idx, __column] = __stat[__column]

            # build numpy array for multidimensional obs metadata
            obs_m = {'ypix': [],
                     'xpix': []}
            for col in [*obs_m]:
                for idx, __stat in enumerate(self.Suite2p.stat):
                    obs_m[col].append(__stat[col])
                obs_m[col] = np.asarray(obs_m[col])

            # SETUP THE VARIABLES ANNOTATIONS TO USE IN anndata
            # build dataframe for var annot's from Paq file
            var_meta = pd.DataFrame(index=[self.Paq.frame_times_channame], columns=range(self.imparams.n_frames))
            for fr_idx in range(self.imparams.n_frames):
                var_meta.loc[self.Paq.frame_times_channame, fr_idx] = self.Paq.frame_clock[fr_idx]

            # BUILD LAYERS TO ADD TO anndata OBJECT
            layers = {'dFF': self.dFF
                      }

            print(f"\n\----- CREATING annotated data object using AnnData:")
            __data_type = 'Suite2p Raw (neuropil substracted)' if self.Suite2p.suite2p_overall.subtract_neuropil else 'Suite2p Raw'
            adata = ad.AnnotatedData(X=self.Suite2p.raw, obs=obs_meta, var=var_meta.T, obsm=obs_m, layers=layers, data_label=__data_type)

            print(f"\n{adata}")
            return adata

        else:
            Warning('did not create anndata. anndata creation only available if experiments were processed with suite2p and .Paq file(s) provided for temporal synchronization')


    def dfof(self):
        if self.Suite2p._s2pResultExists:
            self.dFF = normalize_dff(self.Suite2p.raw)

    def importTrialTiff(self):
        print(f"\n\- loading raw TIFF file from: {self.tiff_path}", end='\r')
        im_stack = tf.imread(self.tiff_path, key=range(self.imparams.n_frames))
        print('|- Loaded experiment tiff of shape: ', im_stack.shape)

        return im_stack

    def meanRawFluTrace(self):
        """
        Collects the raw mean of FOV fluorescence trace across the t-series.

        :param plot: (optional) plot mean fluorescence trace
        :param save: (optional) save data object after collecting mean fluorescence trace
        :return: mean fluorescence trace
        """
        im_stack = self.importTrialTiff()


        print('\n-----collecting mean raw flu trace from tiff file...')
        mean_flu_img = np.mean(im_stack, axis=0)
        mean_fov_flutrace = np.mean(np.mean(im_stack, axis=1), axis=1)

        return mean_flu_img, mean_fov_flutrace

    def makeDownsampledTiff(self):
        stack = self.importTrialTiff()
        SaveDownsampledTiff(stack=stack,
                            save_as=f"{self.analysis_save_dir}/{self.date}_{self.trial}_downsampled.tif")

    def plotSingleImageFrame(self, frame_num: int = 0, title: str = None):
        """
        plots an image of a single specified tiff frame after reading using tifffile.
        :param frame_num: frame # from 2p imaging tiff to show (default is 0 - i.e. the first frame)
        :param title: (optional) give a string to use as title
        :return: matplotlib imshow plot
        """
        stack = tf.imread(self.tiff_path, key=frame_num)
        plt.imshow(stack, cmap='gray')
        plt.suptitle(title) if title is not None else plt.suptitle(f'frame num: {frame_num}' )
        plt.show()
        return stack

    def save_pkl(self, pkl_path: str = None):
        ## commented out after setting pkl_path as a @property
        # if pkl_path is None:
        #     if hasattr(self, 'pkl_path'):
        #         pkl_path = self.pkl_path
        #     else:
        #         raise ValueError(
        #             'pkl path for saving was not found in data object attributes, please provide pkl_path to save to')
        # else:
        #     self.pkl_path = pkl_path
        if pkl_path:
            print(f'saving new trial object to: {pkl_path}')
            self.pkl_path = pkl_path

        with open(self.pkl_path, 'wb') as f:
            pickle.dump(self, f)
        print("\n\t -- data object saved to %s -- " % self.pkl_path)

    def save(self):
        self.save_pkl()


## archived or refactored away class methods or other functions
## REFACTORED PV CODE TO PV MODULE.
def _getPVStateShard(self, root, key):
    '''
    Find the value, description and indices of a particular parameter from an xml file

    Inputs:
        path        - path to xml file
        key         - string corresponding to key in xml tree
    Outputs:
        value       - value of the key
        description - unused
        index       - index that the key was found at
    '''
    value = []
    description = []
    index = []

    pv_state_shard = root.find('PVStateShard')  # find pv state shard element in root

    for elem in pv_state_shard:  # for each element in pv state shard, find the value for the specified key
        if elem.get('key') == key:
            if len(elem) == 0:  # if the element has only one subelement
                value = elem.get('value')
                break

            else:  # if the element has many subelements (i.e. lots of entries for that key)
                for subelem in elem:
                    value.append(subelem.get('value'))
                    description.append(subelem.get('description'))
                    index.append(subelem.get('index'))
        else:
            for subelem in elem:  # if key not in element, try subelements
                if subelem.get('key') == key:
                    value = elem.get('value')
                    break

        if value:  # if found key in subelement, break the loop
            break

    if not value:  # if no value found at all, raise exception
        raise Exception('ERROR: no element or subelement with that key')

    return value, description, index

def _parsePVMetadata(self):
    '''
    Parse all of the relevant acquisition metadata from the PrairieView xml file for this recording
    '''

    print('\n\----- Parsing PV Metadata for Bruker microscope...')


    tiff_path = self.tiff_path_dir  # starting path
    xml_path = []  # searching for xml path

    try:  # look for xml file in path, or two paths up (achieved by decreasing count in while loop)
        count = 2
        while count != 0 and not xml_path:
            count -= 1
            for file in os.listdir(tiff_path):
                if file.endswith('.xml'):
                    xml_path = os.path.join(tiff_path, file)
            tiff_path = os.path.dirname(tiff_path)  # re-assign tiff_path as next folder up

    except:
        raise Exception('ERROR: Could not find xml for this acquisition, check it exists')

    xml_tree = ET.parse(xml_path)  # parse xml from a path
    root = xml_tree.getroot()  # make xml tree structure

    sequence = root.find('Sequence')
    acq_type = sequence.get('type')

    if 'ZSeries' in acq_type:
        n_planes = len(sequence.findall('Frame'))
    else:
        n_planes = 1

    frame_branch = root.findall('Sequence/Frame')[-1]
    #         frame_period = float(self._getPVStateShard(root,'framePeriod')[0])
    frame_period = float(self._getPVStateShard(frame_branch, 'framePeriod')[0])
    fps = 1 / frame_period

    frame_x = int(self._getPVStateShard(root, 'pixelsPerLine')[0])
    frame_y = int(self._getPVStateShard(root, 'linesPerFrame')[0])
    zoom = float(self._getPVStateShard(root, 'opticalZoom')[0])

    scan_volts, _, index = self._getPVStateShard(root, 'currentScanCenter')
    for scan_volts, index in zip(scan_volts, index):
        if index == 'XAxis':
            scan_x = float(scan_volts)
        if index == 'YAxis':
            scan_y = float(scan_volts)

    pixel_size, _, index = self._getPVStateShard(root, 'micronsPerPixel')
    for pixel_size, index in zip(pixel_size, index):
        if index == 'XAxis':
            pix_sz_x = float(pixel_size)
        if index == 'YAxis':
            pix_sz_y = float(pixel_size)

    if n_planes == 1:
        n_frames = root.findall('Sequence/Frame')[-1].get('index')  # use suite2p output instead later
    else:
        n_frames = root.findall('Sequence')[-1].get('cycle')

    extra_params = root.find('Sequence/Frame/ExtraParameters')
    last_good_frame = extra_params.get('lastGoodFrame')

    self.fps = fps / n_planes
    self.frame_x = frame_x
    self.frame_y = frame_y
    self.n_planes = n_planes
    self.pix_sz_x = pix_sz_x
    self.pix_sz_y = pix_sz_y
    self.scan_x = scan_x
    self.scan_y = scan_y
    self.zoom = zoom
    self.n_frames = int(n_frames)
    self.last_good_frame = last_good_frame

    print('\tn planes:', self.n_planes,
          '\n\tn frames:', self.n_frames,
          '\n\tfps:', self.fps,
          '\n\tframe size (px):', self.frame_x, 'x', self.frame_y,
          '\n\tzoom:', self.zoom,
          '\n\tpixel size (um):', self.pix_sz_x, self.pix_sz_y,
          '\n\tscan centre (V):', self.scan_x, self.scan_y
          )