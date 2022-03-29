from conftest import twophoton_imaging_trial_new_noPreDoneSuite2p_fixture
from packerlabimaging import TwoPhotonImagingMain


def test_TwoPhotonImagingTrial_new(twophoton_imaging_trial_new_noPreDoneSuite2p_fixture):
    dict_ = twophoton_imaging_trial_new_noPreDoneSuite2p_fixture()
    return TwoPhotonImagingMain.TwoPhotonImagingTrial(**dict_['t-005'])

trialobj = test_TwoPhotonImagingTrial_new(twophoton_imaging_trial_new_noPreDoneSuite2p_fixture)

def test_TwoPhotonImagingTrial(twophoton_imaging_trial_fixture):
    TwoPhotonImagingMain.TwoPhotonImagingTrial(**twophoton_imaging_trial_fixture)


def test_meanRawFluTrace(existing_trialobj_twophotonimaging_fixture):
    trialobj: TwoPhotonImagingMain.TwoPhotonImagingTrial = existing_trialobj_twophotonimaging_fixture[0]
    trialobj.meanFluImg, trialobj.meanFovFluTrace = trialobj.meanRawFluTrace()
    trialobj.save()

# TODO add tests for main public functions - especially those in tutorial 1