# library of convenience plotting funcs that are used for making various plots for all optical photostimulation/imaging experiments

# imports
import os
from typing import Union

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import tifffile as tf

from packerlabimaging import Experiment

from packerlabimaging.AllOpticalMain import AllOpticalTrial

from packerlabimaging.TwoPhotonImagingMain import TwoPhotonImagingTrial
from packerlabimaging.plotting._utils import plotting_decorator, make_random_color_array, _add_scalebar, \
    image_frame_options, dataplot_frame_options, dataplot_ax_options, plot_coordinates, heatmap_options, image_frame_ops
from packerlabimaging.processing.paq import PaqData
from packerlabimaging.utils.classes import ObjectClassError


# DATA ANALYSIS PLOTTING FUNCS

# suite2p data
# simple plot of the location of the given cell(s) against a black FOV
@mpl.rc_context(image_frame_ops)
@plotting_decorator(figsize=(5, 5))
def plotRoiLocations(trialobj: TwoPhotonImagingTrial, suite2p_rois: Union[list, str] = 'all',
                     background: np.ndarray = None, **kwargs):
    """
    plots an image of the FOV to show the locations of cells given in cells ls.

    :param trialobj: alloptical or 2p imaging object
    :param background: either 2dim numpy array to use as the backsplash or None (default; which is a black background)
    :param suite2p_rois: list of ROIs (suite2p cell IDs) to show coord location, default is 'all' (which is all ROIs)
    :param edgecolor: specify edgecolor of the scatter plot for cells
    :param facecolor: specify facecolor of the scatter plot for cells
    :param cells: list of cells to plot
    :param title: title for plot
    :param color_float_list: if given, it will be used to color the cells according a colormap
    :param cmap: cmap to be used in conjuction with the color_float_array argument
    :param show_s2p_targets: if True, then will prioritize coloring of cell points based on whether they were photostim targets
    :param invert_y: if True, invert the reverse the direction of the y axis
    :param fig: a matplotlib.Figure instance, if provided use this fig for plotting
    :param ax: a matplotlib.Axes.axes instance, if provided use this ax for plotting
    :param show: if False, do not display plot (used when the necessity is to return the fig and ax objects to futher manipulation)
    :returns fig, ax: returns fig and ax object, if show is False
    """
    # image_frame_options()

    # fig = kwargs['fig']
    # suptitle = kwargs['suptitle'] if 'suptitle' in [*kwargs] else None
    image_frame_options() if 'apply_image_frame_options' not in [*kwargs] or kwargs[
        'apply_image_frame_options'] else None

    ax = kwargs['ax']
    kwargs.pop('ax')

    facecolors = kwargs['facecolors'] if 'facecolors' in [*kwargs] else 'none'
    edgecolors = kwargs['edgecolors'] if 'edgecolors' in [*kwargs] else 'orange'

    if suite2p_rois == 'all':
        suite2p_rois = trialobj.Suite2p.cell_id

    for cell in suite2p_rois:
        y, x = trialobj.Suite2p.stat[trialobj.Suite2p.cell_id.index(cell)]['med']
        ax.scatter(x=x, y=y, edgecolors=edgecolors, facecolors=facecolors, linewidths=0.8)

    if background is None:
        black = np.zeros((trialobj.imparams.frame_x, trialobj.imparams.frame_y), dtype='uint16')
        ax.imshow(black, cmap='Greys_r', zorder=0)
        ax.set_xlim(0, trialobj.imparams.frame_x)
        ax.set_ylim(0, trialobj.imparams.frame_y)
    else:
        ax.imshow(background, cmap='Greys_r', zorder=0)

    ax.invert_yaxis()

    _add_scalebar(trialobj=trialobj, ax=ax) if 'scalebar' in [*kwargs] and kwargs['scalebar'] is True else None
    mpl.pyplot.rcdefaults()


@mpl.rc_context(image_frame_ops)
@plotting_decorator(figsize=(15, 5), nrows=1, ncols=4)
def makeSuite2pPlots(obj: Union[Experiment, TwoPhotonImagingTrial], **kwargs):
    """
    Makes four plots that are created by Suite2p output.

    credit: run_s2p tutorial on Mouseland/Suite2p on github

    :param obj: Experiment or Trial object to use for creating Suite2p plots.
    :param axs: a matplotlib.Axes.axes instance (4 cols x 1 rows), if provided use these axes for plotting
    :param show: if False, do not display plot (used when the necessity is to return the fig and ax objects to futher manipulation)
    :returns fig, axs: returns fig and ax object, if show is False

    """

    heatmap_options()

    axs = kwargs['axs']
    kwargs.pop('axs')

    # f, axs = plt.subplots(figsize=[15, 5], nrows=1, ncols=4)

    # plt.subplot(1, 4, 1)
    axs[0].imshow(obj.Suite2p.output_ops['meanImgE'], cmap='gray')
    axs[0].set_title("Registered Image, Mean Enhanced", wrap=True)

    # plt.subplot(1, 4, 2)
    axs[1].imshow(np.nanmax(obj.Suite2p.im, axis=0), cmap='jet')
    axs[1].set_title("All ROIs Found", wrap=True)

    # plt.subplot(1, 4, 3)
    axs[2].imshow(np.nanmax(obj.Suite2p.im[~obj.Suite2p.iscell], axis=0, ), cmap='jet')
    axs[2].set_title("All Non-Cell ROIs", wrap=True)

    # plt.subplot(1, 4, 4)
    axs[3].imshow(np.nanmax(obj.Suite2p.im[obj.Suite2p.iscell], axis=0), cmap='jet')
    axs[3].set_title("All Cell ROIs", wrap=True)

    _add_scalebar(trialobj=obj, ax=axs[3]) if 'scalebar' in [*kwargs] and kwargs['scalebar'] is True else None
    mpl.pyplot.rcdefaults()


@plotting_decorator(figsize=(20, 3))
def plot_flu_trace(trialobj: TwoPhotonImagingTrial, cell, to_plot='raw', **kwargs):
    """
    plot individual cell's flu or dFF trace, with photostim. timings for that cell

    :param trialobj: trialobject to plot
    :param cell:
    :param to_plot:
    :param fig: a matplotlib.Figure instance, if provided use this fig for plotting
    :param ax: a matplotlib.Axes.axes instance, if provided use this ax for plotting
    :param show: if False, do not display plot (used when the necessity is to return the fig and ax objects to futher manipulation)
    :returns fig, ax: returns fig and ax object, if show is False
    """
    dataplot_frame_options()
    ax = kwargs['ax']
    kwargs.pop('ax')
    for i in ['lw', 'linewidth']:
        try:
            lw = kwargs[i]
        except KeyError:
            lw = 1

    idx = trialobj.Suite2p.cell_id.index(cell)

    if to_plot == 'raw':
        data_to_plot = trialobj.data.X[idx, :]
    else:
        if to_plot in [*trialobj.data.layers]:
            data_to_plot = trialobj.data.layers[to_plot][idx, :]
        else:
            raise KeyError(f"to_plot processed data is not found in trialobj.data.layers. ")

    # make the plot either as just the raw trace or as a dFF trace with the std threshold line drawn as well.
    ax.plot(data_to_plot, linewidth=lw)

    dataplot_ax_options(ax=ax, data_length=len(data_to_plot), **kwargs)
    mpl.pyplot.rcdefaults()


@plotting_decorator()
def plot__paq_channel(paqData: PaqData, channel: str, **kwargs):
    """
    Plot the stored signal from the specified channel from a PaqData submodule.

    :param paqData: .Paq submodule data
    :param channel:
    :param kwargs:
        x_axis: str, x axis label, if 'time' or "Time" found in x_axis label, will convert x axis to time domain.
        x_tick_secs: int, interval to plot x axis ticks
        ax: matplotlib axis object to use for plotting.
    """
    assert channel in paqData.paq_channels, f'{channel} not found in .Paq module data.'

    # set any kwargs provided
    ax = kwargs['ax']
    kwargs.pop('ax')

    # kwargs['x_axis'] = 'Time (secs)' if 'x_axis' not in [*kwargs] else kwargs['x_axis']
    kwargs['x_tick_secs'] = 120 if 'x_tick_secs' not in [*kwargs] else kwargs['x_tick_secs']

    lw = 0.5 if 'lw' not in [*kwargs] else kwargs['lw']
    color = 'black' if 'color' not in [*kwargs] else kwargs['color']

    # collect data to plot
    data = getattr(paqData, channel)

    # make plot
    x = np.linspace(0, len(data)/paqData.paq_rate, len(data))
    ax.plot(x, data, lw=lw, color=color)
    ax.set_title(f"{channel}")
    ax.set_ylim(kwargs['y_lims']) if 'y_lims' in kwargs else None
    ax.set_xlabel('Time (secs)')
    ax.set_xticks([label for label in range(0, int(len(data) / paqData.paq_rate), kwargs['x_tick_secs'])])
    ax.set_xlabel(kwargs['x_axis'])
    # from packerlabimaging.plotting._utils import dataplot_ax_options
    # dataplot_ax_options(ax=ax, data_length=len(data), collection_hz=paqData.paq_rate, **kwargs)
    # dataplot_ax_options(ax=ax, data_length=len(data), collection_hz=1, **kwargs)
    ax.grid(True)



def makeFrameAverageTiff(tiff_path: str, frames: Union[int, list], peri_frames: int = 100, save_dir: str = None, to_plot=False):
    """
    Creates, plots and/or saves an average image of the specified number of peri-frames around the given frame from a multipage imaging TIFF file.

    :param peri_frames:
    :param save_img:
    :param to_plot:
    :param force_redo:
    :param verbose:
    :return:
    """

    print('\nMaking peri-frame avg image...')

    if type(frames) == int:
        frames = [frames]

    # read tiff
    print(f'\t\- Creating avg img for frame: {frames}, from tiff: {tiff_path}')
    im_stack = tf.imread(tiff_path)

    for frame in frames:
        if frame < peri_frames // 2:
            peri_frames_low = frame
        else:
            peri_frames_low = peri_frames // 2
        peri_frames_high = peri_frames // 2
        im_sub = im_stack[frame - peri_frames_low: frame + peri_frames_high]
        avg_sub = np.mean(im_sub, axis=0)

        # convert to 8-bit
        from packerlabimaging.utils.utils import convert_to_8bit
        avg_sub = convert_to_8bit(avg_sub, 0, 255)

        if save_dir:
            if '.tif' in save_dir:
                from packerlabimaging.utils.utils import return_parent_dir
                save_dir = return_parent_dir(save_dir) + '/'
            save_path = save_dir + f'/{frame}_frame_avg.tif'
            os.makedirs(save_dir, exist_ok=True)

            print(f"\t\- Saving averaged tiff for frame: {frame}, to: {save_path}")
            tf.imwrite(save_path, avg_sub, photometric='minisblack')

        if to_plot:
            plt.imshow(avg_sub, cmap='gray')
            plt.suptitle(f'{peri_frames} peri-frames avg from frame {frame}')
            plt.show()  # just plot for now to make sure that you are doing things correctly so far


def showSingleTiffFrame(tiff_path, frame_num: int = 0, title: str = None):
    """
    plots an image of a single specified tiff frame after reading using tifffile.

    :param tiff_path: path to .tiff file to loads
    :param frame_num: frame # from 2p imaging tiff to show (default is 0 - i.e. the first frame)
    :param title: (optional) give a string to use as title
    :return: matplotlib imshow plot
    """
    stack = tf.imread(tiff_path, key=frame_num)
    plt.imshow(stack, cmap='gray')
    plt.suptitle(title) if title is not None else plt.suptitle(f'frame num: {frame_num}')
    plt.show()
    return stack


# plots the raw trace for the Flu mean of the FOV (similar to the ZProject in Fiji)
@plotting_decorator(figsize=(10, 3))
def plotMeanFovFluTrace(trialobj: TwoPhotonImagingTrial, **kwargs):
    """make plot of mean Ca trace averaged over the whole FOV

    :param fig: a matplotlib.Figure instance, if provided use this fig for plotting
    :param ax: a matplotlib.Axes.axes instance, if provided use this ax for plotting
    :param show: if False, do not display plot (used when the necessity is to return the fig and ax objects to futher manipulation)
    :returns fig, ax: returns fig and ax object, if show is False
    """

    if not hasattr(trialobj, 'meanFovFluTrace'):
        raise AttributeError('Cannot make plot. Missing meanFovFluTrace attribute.')

    else:
        dataplot_frame_options()
        ax = kwargs['ax']
        kwargs.pop('ax')
        for i in ['lw', 'linewidth']:
            try:
                lw = kwargs[i]
            except KeyError:
                lw = 1

        data_to_plot = trialobj.meanFovFluTrace

        print(f"\t \- PLOTTING mean raw flu trace ... ")
        ax.plot(data_to_plot, c='forestgreen', linewidth=lw)

        ax.set_xlabel('frame #s')
        ax.set_ylabel('Flu (a.u.)')

        dataplot_ax_options(ax=ax, data_length=len(data_to_plot), collection_hz=trialobj.imparams.fps, **kwargs)


@plotting_decorator(figsize=(10, 6))
def plot_photostim_traces_overlap(array, trialobj: AllOpticalTrial, exclude_id=[], y_spacing_factor=1, title='',
                                  x_axis='Time (seconds)', **kwargs):
    """
    :param array:
    :param trialobj:
    :param spacing: a multiplication factor that will be used when setting the spacing between each trace in the final plot
    :param title:
    :param y_min:
    :param y_max:
    :param x_label:
    :param save_fig:
    :param fig: a matplotlib.Figure instance, if provided use this fig for plotting
    :param ax: a matplotlib.Axes.axes instance, if provided use this ax for plotting
    :param show: if False, do not display plot (used when the necessity is to return the fig and ax objects to futher manipulation)
    :returns fig, ax: returns fig and ax object, if show is False

    """

    len_ = len(array)
    dataplot_frame_options()
    ax = kwargs['ax']
    kwargs.pop('ax')

    for i in range(len_):
        if i not in exclude_id:
            if 'linewidth' in kwargs.keys():
                linewidth = kwargs['linewidth']
            else:
                linewidth = 1
            ax.plot(array[i] + i * 40 * y_spacing_factor, linewidth=linewidth)
    for j in trialobj.stim_start_frames:
        if j <= array.shape[1]:
            ax.axvline(x=j, c='gray', alpha=0.3)

    ax.set_xlim([0, trialobj.n_frames - 3000])

    ax.margins(0)
    # change x axis ticks to seconds
    if 'Time' in x_axis or 'time' in x_axis:
        # change x axis ticks to every 30 seconds
        labels = list(range(0, int(trialobj.n_frames // trialobj.imparams.fps), 30))
        ax.set_xticks(ticks=[(label * trialobj.imparams.fps) for label in labels])
        ax.set_xticklabels(labels)
        ax.set_xlabel('Time (secs)')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.set_xlabel(x_axis)

    if 'y_lim' in kwargs.keys():
        ax.set_ylim(kwargs['y_lim'])
    else:
        y_max = np.mean(array[-1] + len_ * 40 * y_spacing_factor) + 3 * np.mean(array[-1])
        ax.set_ylim(0, y_max)

    ax.set_title((title + ' - %s' % len_ + ' cells'), horizontalalignment='center', verticalalignment='top', pad=20,
                 fontsize=10, wrap=True)

    dataplot_ax_options(ax=ax, data_length=array.shape[1], **kwargs)


def plot_s2p_raw(trialobj, cell_id):
    """

    :param trialobj:
    :param cell_id:
    """
    plt.figure(figsize=(50, 3))
    plt.plot(trialobj.baseline_raw[trialobj.cell_id.index(cell_id)], linewidth=0.5, c='black')
    plt.xlim(0, len(trialobj.baseline_raw[0]))
    plt.show()


# suite2p data


# LFP
@plotting_decorator(figsize=(10, 3))
def plotLfpSignal(trialobj: TwoPhotonImagingTrial, stim_span_color='powderblue', downsample: bool = True,
                  stim_lines: bool = True, sz_markings: bool = False,
                  title='LFP trace', x_axis='time', hide_xlabel=False, fig=None, ax=None, **kwargs):
    """make plot of LFP with also showing stim locations
    NOTE: ONLY PLOTTING LFP SIGNAL CROPPED TO 2P IMAGING FRAME START AND END TIMES - SO CUTTING OUT THE LFP SIGNAL BEFORE AND AFTER

    :param trialobj:
    :param stim_span_color:
    :param downsample:
    :param stim_lines:
    :param sz_markings:
    :param title:
    :param x_axis:
    :param hide_xlabel:
    :param fig: a matplotlib.Figure instance, if provided use this fig for plotting
    :param ax: a matplotlib.Axes.axes instance, if provided use this ax for plotting
    :param show: if False, do not display plot (used when the necessity is to return the fig and ax objects to futher manipulation)
    :returns fig, ax: returns fig and ax object, if show is False

    """

    print(f"\t \- PLOTTING LFP Signal trace ... ")

    if not hasattr(trialobj.Paq, 'voltage'):
        raise AttributeError(f"no voltage data found in .Paq submodule. Please add to .Paq file")

    if 'alpha' in kwargs:
        alpha = kwargs['alpha']
    else:
        alpha = 1

    # plot LFP signal
    if 'color' in kwargs:
        color = kwargs['color']
    else:
        color = 'steelblue'

    # option for downsampling of data plot trace
    x = range(len(trialobj.Paq.voltage[trialobj.Paq.frame_times[0]: trialobj.Paq.frame_times[-1]]))
    signal = trialobj.Paq.voltage[trialobj.Paq.frame_times[0]: trialobj.Paq.frame_times[-1]]
    if downsample:
        labels = list(range(0, int(len(signal) / trialobj.Paq.paq_rate * 1), 15))[::2]  # set x ticks at every 30 secs
        down = 1000
        signal = signal[::down]
        x = x[::down]
        assert len(x) == len(signal), print('something went wrong with the downsampling')

    # change linewidth
    if 'linewidth' in kwargs:
        lw = kwargs['linewidth']
    else:
        lw = 0.4

    ax.plot(x, signal, c=color, zorder=1, linewidth=lw)  ## NOTE: ONLY PLOTTING LFP SIGNAL RELATED TO
    ax.margins(0.02)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    # ax.spines['left'].set_visible(False)

    # change x axis ticks to seconds
    labels_ = kwargs['labels'] if 'labels' in [*kwargs] else ax.get_xticklabels()
    labels_ = [int(i) for i in labels_]
    if 'time' in x_axis or 'Time' in x_axis:
        ax.set_xticks(ticks=[(label * trialobj.Paq.paq_rate) for label in labels_])
        ax.set_xticklabels(labels_)
        ax.tick_params(axis='both', which='both', length=3)
        if not hide_xlabel:
            ax.set_xlabel('Time (secs)')
    # elif 'frame' or "frames" or "Frames" or "Frame" in x_axis:
    #     x_ticks = range(0, trialobj.n_frames, 2000)
    #     x_clocks = [x_fr*trialobj.paq_rate for x_fr in x_ticks]  ## convert to Paq clock dimension
    #     ax.set_xticks(x_clocks)
    #     ax.set_xticklabels(x_ticks)
    #     if not hide_xlabel:
    #         ax.set_xlabel('Frames')
    else:
        ax.set_xlabel('Paq clock')
    ax.set_ylabel('Voltage')
    # ax.set_xlim([trialobj.imparams.frame_start_time_actual, trialobj.imparams.frame_end_time_actual])  ## this should be limited to the 2p acquisition duration only

    # set ylimits:
    if 'ylims' in kwargs:
        ax.set_ylim(kwargs['ylims'])
    else:
        ax.set_ylim([np.mean(trialobj.Paq.voltage) - 10, np.mean(trialobj.Paq.voltage) + 10])

    # set xlimits:
    if 'xlims' in kwargs and kwargs['xlims'] is not None:
        ax.set_xlim(kwargs['xlims'])

    # add title
    ax.set_title(f"{trialobj.t_series_name}")

    # return None
    # if not 'fig' in kwargs.keys():
    #     ax.set_title(
    #         '%s - %s %s %s' % (title, trialobj.metainfo['exptype'], trialobj.metainfo['exp_id'], trialobj.metainfo['trial_id']))
    #
    # # options for showing plot or returning plot
    # if 'show' in kwargs.keys():
    #     plt.show() if kwargs['show'] else None
    # else:
    #     plt.show()

    # return fig, ax if 'fig' in kwargs.keys() else None


# LFP


### plot entire trace of individual targeted cells as super clean subplots, with the same y-axis lims
def plot_photostim_traces(array, trialobj: AllOpticalTrial, title='', y_min=None, y_max=None, x_label=None,
                          y_label=None, save_fig=None, **kwargs):
    """

    :param array:
    :param trialobj:
    :param title:
    :param y_min:
    :param y_max:
    :param x_label:
    :param y_label:
    :param save_fig:
    :param kwargs:
        options include:
            hits: ls; a ls of 1s and 0s that is used to add a scatter point to the plot at stim_start_frames indexes at 1s
    :return:
    """
    # make rolling average for these plots
    w = 30
    array = [(np.convolve(trace, np.ones(w), 'valid') / w) for trace in array]

    len_ = len(array)
    fig, axs = plt.subplots(nrows=len_, sharex=True, figsize=(20, 3 * len_))
    for i in range(len(axs)):
        axs[i].plot(array[i], linewidth=1, color='black', zorder=2)
        if y_min != None:
            axs[i].set_ylim([y_min, y_max])
        for j in trialobj.stim_start_frames:
            axs[i].axvline(x=j, c='gray', alpha=0.7, zorder=1)
        if 'scatter' in kwargs.keys():
            x = trialobj.stim_start_frames[kwargs['scatter'][i]]
            y = [0] * len(x)
            axs[i].scatter(x, y, c='chocolate', zorder=3)
        if len_ == len(trialobj.s2p_cell_targets):
            axs[i].set_title('Cell # %s' % trialobj.s2p_cell_targets[i])
        if 'line_ids' in kwargs:
            axs[i].legend(['Target %s' % kwargs['line_ids'][i]], loc='upper left')

    axs[0].set_title((title + ' - %s' % len_ + ' cells'), loc='left', verticalalignment='top', pad=20,
                     fontsize=15)
    axs[0].set_xlabel(x_label)
    axs[0].set_ylabel(y_label)

    if save_fig is not None:
        plt.savefig(save_fig)

    fig.show()


### photostim analysis - PLOT avg over photostim. trials traces for the provided traces
@plotting_decorator(figsize=(5, 5.5))
def plot_periphotostim_avg2(dataset, fps=None, legend_labels=None, colors=None, avg_with_std=False,
                            title='high quality plot', pre_stim_sec=None, ylim=None, fig=None, ax=None, **kwargs):
    # if 'fig' in kwargs.keys():
    #     fig = kwargs['fig']
    #     ax = kwargs['ax']
    # else:
    #     if 'figsize' in kwargs.keys():
    #         fig, ax = plt.subplots(figsize=kwargs['figsize'])
    #     else:
    #         fig, ax = plt.subplots(figsize=[5, 4])

    meantraces = []
    stdtraces = []
    if type(dataset) == list and len(dataset) > 1:
        assert len(legend_labels) == len(dataset), print('please provide same number of legend labels as dataset')
        if colors is None:
            colors = ['black', make_random_color_array(len(dataset) - 1)]
        assert len(colors) == len(legend_labels)
        avg_only = True
        print('-- plotting average +/- std fill for each dataset')
        for i in range(len(dataset)):
            meanst = np.mean(dataset[i], axis=0)
            std = np.std(dataset[i], axis=0, ddof=1)
            meantraces.append(meanst)
            stdtraces.append(std)
            if not meanst.shape == meantraces[i - 1].shape:
                print(
                    f"|--- length mismatch in mean traces of datasets... {title}, shape0 {meanst.shape} and shape1 {meantraces[i - 1].shape}")
            if not std.shape == stdtraces[i - 1].shape:
                print(
                    f"|--- length mismatch in std traces of datasets...{title}, shape0 {std.shape} and shape1 {stdtraces[i - 1].shape}")

    elif type(dataset) is not list or len(dataset) == 1:
        dataset = list(dataset)
        meanst = np.mean(dataset[0], axis=0)
        std = np.std(dataset[0], axis=0, ddof=1)
        meantraces.append(meanst)
        stdtraces.append(std)
        colors = ['black']
    else:
        AttributeError('please provide the data to plot in a ls format, each different data group as a ls item...')

    if 'xlabel' not in kwargs or kwargs['xlabel'] is None or 'frames' not in kwargs['xlabel'] or 'Frames' not in kwargs[
        'xlabel']:
        ## change xaxis to time (secs)
        if fps is not None:
            if pre_stim_sec is not None:
                x_range = np.linspace(0, len(meantraces[0]) / fps, len(
                    meantraces[
                        0])) - pre_stim_sec  # x scale, but in time domain (transformed from frames based on the provided fps)
                if 'xlabel' in kwargs.keys():
                    ax.set_xlabel(kwargs['xlabel'])
                else:
                    ax.set_xlabel('Time post stim (secs)')
            else:
                AttributeError('need to provide a pre_stim_sec value to the function call!')
        else:
            AttributeError('need to provide fps value to convert xaxis in units of time (secs)')
    elif 'frames' in kwargs['xlabel'] or 'Frames' in kwargs['xlabel']:
        x_range = range(len(meanst[0]))
        ax.set_xlabel('Frames')

    for i in range(len(meantraces)):
        if avg_with_std:
            if len(meantraces[i]) < len(x_range):  ## TEMP FIX
                mismatch = (len(x_range) - len(meantraces[i]))
                meantraces[i] = np.append(meantraces[i], [0] * mismatch)
                stdtraces[i] = np.append(stdtraces[i], [0] * mismatch)
                print(
                    f'|------ adding {mismatch} zeros to mean and std-fill traces to make the arrays the same length, new length of plot array: {meantraces[i].shape} ')

            ax.plot(x_range, meantraces[i], color=colors[i], lw=2)
            ax.fill_between(x_range, meantraces[i] - stdtraces[i], meantraces[i] + stdtraces[i], alpha=0.15,
                            color=colors[i])
        else:
            ax.plot(x_range, meantraces[i], color=colors[i], lw=2)
            for trace in dataset[i]:
                ax.plot(x_range, trace, color=colors[i], alpha=0.3, lw=2)

    if legend_labels:
        if 'fontsize' in kwargs.keys():
            fontsize = kwargs['fontsize']
        else:
            fontsize = 'medium'
        ax.legend(legend_labels, fontsize=fontsize)
    if ylim:
        ax.set_ylim([ylim[0], ylim[1]])
    if 'ylabel' in kwargs.keys():
        ax.set_ylabel(kwargs['ylabel'])
    else:
        pass

    if 'savepath' in kwargs.keys():
        plt.savefig(kwargs['savepath'])

    # # finalize plot, set title, and show or return axes
    # ax.set_title(title)
    # if 'show' in kwargs.keys():
    #     fig.show() if kwargs['show'] else None
    # else:
    #     fig.show()
    #
    # if 'fig' in kwargs.keys():
    #     return fig, ax


### photostim analysis - PLOT avg over all photstim. trials traces from PHOTOSTIM TARGETTED cells
@plotting_decorator(figsize=(5, 5.5))
def plot_periphotostim_avg(arr: np.ndarray, trialobj: AllOpticalTrial, pre_stim_sec=1.0, post_stim_sec=3.0, title='',
                           avg_only: bool = False, x_label=None, y_label=None, pad=20, **kwargs):
    """
    plot trace across all stims
    :param arr: Flu traces to plot (will be plotted as individual traces unless avg_only is True) dimensions should be cells x stims x frames
    :param trialobj: instance object of AllOpticalTrial
    :param pre_stim_sec: seconds of array to plot for pre-stim period
    :param post_stim_sec: seconds of array to plot for post-stim period
    :param title: title to use for plot
    :param avg_only: if True, only plot the mean trace calculated from the traces provided in arr
    :param x_label: x axis label
    :param y_label: y axis label
    :param kwargs:
        options include:
            'stim_duration': photostimulation duration in secs
            'y_lims': tuple, y min and max of the plot
            'edgecolor': str, edgecolor of the individual traces behind the mean trace
            'savepath': str, path to save plot to

    :param fig: a matplotlib.Figure instance, if provided use this fig for plotting
    :param ax: a matplotlib.Axes.axes instance, if provided use this ax for plotting
    :param show: if False, do not display plot (used when the necessity is to return the fig and ax objects to futher manipulation)
    :returns fig, ax: returns fig and ax object, if show is False

    """

    fps = trialobj.imparams.fps  # frames per second rate of the imaging data collection for the data to be plotted
    exp_prestim = trialobj.pre_stim_frames  # frames of pre-stim data collected for each trace for this trialobj (should be same as what's under trialobj.pre_stim_sec)
    if 'stim_duration' in kwargs.keys():
        stim_duration = kwargs['stim_duration']
    else:
        stim_duration = trialobj.Targets.stim_dur / 1000  # seconds of stimulation duration

    dataplot_frame_options()
    ax = kwargs['ax']
    kwargs.pop('ax')

    x = list(range(arr.shape[1]))
    # x range in time (secs)
    x_time = np.linspace(0, arr.shape[1] / fps, arr.shape[
        1]) - pre_stim_sec  # x scale, but in time domain (transformed from frames based on the provided fps)

    len_ = len(arr)
    flu_avg = np.mean(arr, axis=0)

    # ax.margins(x=0.07)

    if 'alpha' in kwargs.keys():
        alpha = kwargs['alpha']
    else:
        alpha = 0.2

    if x_label is None or not 'Frames' in x_label or 'frames' in x_label:
        x = x_time  # set the x plotting range
        if x_label is not None:
            x_label = x_label + 'post-stimulation relative'
        else:
            x_label = 'Time (secs post-stimulation)'

        if avg_only is True:
            # ax.axvspan(exp_prestim/fps, (exp_prestim + stim_duration + 1) / fps, alpha=alpha, color='plum', zorder = 3)
            ax.axvspan(0 - 1 / fps, 0 + stim_duration + 1 / fps, alpha=alpha, color='plum',
                       zorder=3)  # note that we are setting 0 as the stimulation time
        else:
            ax.axvspan(0 - 1 / fps, 0 - 1 / fps + stim_duration, alpha=alpha, color='plum',
                       zorder=3)  # note that we are setting 0 as the stimulation time
    else:
        ax.axvspan(exp_prestim, exp_prestim + int(stim_duration * fps), alpha=alpha, color='tomato')

    if not avg_only:
        for cell_trace in arr:
            if 'color' in kwargs.keys():
                ax.plot(x, cell_trace, linewidth=1, alpha=0.6, c=kwargs['color'], zorder=1)
            else:
                if arr.shape[0] > 50:
                    alpha = 0.1
                else:
                    alpha = 0.5
                ax.plot(x, cell_trace, linewidth=1, alpha=alpha, zorder=1)

    ax.plot(x, flu_avg, color='black', linewidth=2.3, zorder=2)  # plot average trace

    if 'y_lims' in kwargs.keys():
        ax.set_ylim(kwargs['y_lims'])
    if pre_stim_sec and post_stim_sec:
        if x_label is None or not 'Frames' in x_label or 'frames' in x_label:
            ax.set_xlim(-pre_stim_sec,
                        stim_duration + post_stim_sec)  # remember that x axis is set to be relative to the stim time (i.e. stim is at t = 0)
        else:
            ax.set_xlim(exp_prestim - int(pre_stim_sec * fps),
                        exp_prestim + int(stim_duration * fps) + int(post_stim_sec * fps) + 1)

    # set axis labels
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)

    if 'savepath' in kwargs.keys():
        plt.savefig(kwargs['savepath'])

    if title is not None:
        ax.set_title((title + ' - %s' % len_ + ' traces'), horizontalalignment='center', verticalalignment='top',
                     pad=pad, fontsize=10, wrap=True)

    dataplot_ax_options(ax=ax, data_length=arr.shape[1], **kwargs)


# alloptical trial
### plot the location of all SLM targets, along with option for plotting the mean img of the current trial

@mpl.rc_context(image_frame_ops)
@plotting_decorator(figsize=(5, 5))
def plot_SLMtargets_Locs(trialobj: AllOpticalTrial, targets_coords: Union[list, str] = 'all',
                         background: np.ndarray = None, **kwargs):
    """
    plot SLM target coordinate locations

    :param trialobj:
    :param targets_coords: ls containing (x,y) coordinates of targets to plot
    :param background:
    :param kwargs:
    :param fig: a matplotlib.Figure instance, if provided use this fig for plotting
    :param ax: a matplotlib.Axes.axes instance, if provided use this ax for plotting
    :param show: if False, do not display plot (used when the necessity is to return the fig and ax objects to futher manipulation)
    :returns fig, ax: returns fig and ax object, if show is False

    """

    if not type(trialobj) == AllOpticalTrial:
        raise ObjectClassError(function='plot_SLMtargets_Locs', valid_class=[AllOpticalTrial],
                               invalid_class=type(trialobj))
    ax = kwargs['ax']
    fig = kwargs['fig']
    kwargs.pop('ax')

    if background is None:
        background = np.zeros((trialobj.imparams.frame_x, trialobj.imparams.frame_y), dtype='uint16')
        ax.imshow(background, cmap='gray')
    else:
        ax.imshow(background, cmap='gray')

    colors = make_random_color_array(len(trialobj.Targets.target_coords))
    if targets_coords is 'all':
        if len(trialobj.Targets.target_coords) > 1:
            for i in range(len(trialobj.Targets.target_coords)):
                ax.scatter(x=trialobj.Targets.target_coords[i][:, 0], y=trialobj.Targets.target_coords[i][:, 1],
                           edgecolors=colors[i], facecolors='none', linewidths=2.0, label=f'SLM Group {i}')
                # for (x, y) in trialobj.Targets.target_coords[i]:
                #     ax.scatter(x=x, y=y, edgecolors=colors[i], facecolors='none', linewidths=2.0)
        else:
            if 'edgecolors' in kwargs.keys():
                edgecolors = kwargs['edgecolors']
            else:
                edgecolors = 'yellowgreen'
            for (x, y) in trialobj.Targets.target_coords_all:
                ax.scatter(x=x, y=y, edgecolors=edgecolors, facecolors='none', linewidths=2.0)
    elif targets_coords:
        if 'edgecolors' in kwargs.keys():
            edgecolors = kwargs['edgecolors']
        else:
            edgecolors = 'yellowgreen'
        plot_coordinates(coords=targets_coords, frame_x=trialobj.imparams.frame_x, frame_y=trialobj.imparams.frame_y,
                         edgecolors=edgecolors,
                         background=background, fig=fig, ax=ax)

    ax.legend(loc='upper right', labelcolor='white', frameon=False)
    ax.margins(0)

    ax = _add_scalebar(trialobj=trialobj, ax=ax)

    # fig.tight_layout()

    if 'title' in kwargs.keys():
        if kwargs['title'] is not None:
            ax.set_title(kwargs['title'])
        else:
            pass
    else:
        ax.set_title(f'SLM targets location - {trialobj.t_series_name}')

    # mpl.pyplot.rcdefaults()
    # fig.show()


# alloptical trial


def plot_s2pMasks():
    """ Creates some images of SLM targets to suite2p.

    """
    pass
