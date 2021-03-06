import packerlabimaging as pli
from conftest import alloptical_trial_fixture
from packerlabimaging import AllOpticalTrial

# %%


# %%

# def test_AllOpticalClass(alloptical_trial_fixture):
#     aotrial = AllOpticalTrial(**alloptical_trial_fixture)
#     return aotrial
#
# idict = alloptical_trial_fixture()
# aotrial = test_AllOpticalClass(idict)


def test_processing_targets_stims(existing_trialobj_alloptical_fixture):
    self = existing_trialobj_alloptical_fixture
    self.twopstim, self.stim_duration_frames = self.photostimProcessing()

    self.raw_SLMTargets, self.dFF_SLMTargets, self.meanFluImg_registered = self.collectSignalFromCoords(
        curr_trial_frames=self.Suite2p.trial_frames, save=True)
    self.targets_dff, self.targets_dff_avg, self.targets_dfstdF, self.targets_dfstdF_avg, \
    self.targets_raw, self.targets_raw_avg = self.getTargetsStimTraceSnippets()
    self.save()

# %%
# import packerlabimaging as pkg
#
# expobj = pkg.import_obj('/home/pshah/Documents/code/packerlabimaging/tests/RL109_analysis.pkl')
# trial = expobj.load_trial('t-013')
#
# trial.cellsdata
#
