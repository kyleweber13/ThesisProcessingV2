import pyedflib
from datetime import datetime
from datetime import timedelta
import pandas as pd
import numpy as np
from ecgdetectors import Detectors  # https://github.com/luishowell/ecg-detectors
import scipy.stats as stats
import progressbar
from random import randint
from scipy.signal import butter, lfilter, filtfilt


class Bittium:

    def __init__(self, filepath, epoch_len=15, load_accel=False,
                 filter_data=True, low_f=1, high_f=30, f_order=2, f_type="bandpass"):

        self.filepath = filepath
        self.epoch_len = epoch_len
        self.load_accel = load_accel

        # Filter details
        self.filter_data = filter_data
        self.low_f = low_f
        self.high_f = high_f
        self.f_order = f_order
        self.f_type = f_type

        # ECG data
        self.raw = None
        self.filtered = None
        self.timestamps = None
        self.epoch_timestamps = None

        # Accel data
        self.accel_sample_rate = 1  # default value
        self.x = None
        self.y = None
        self.z = None
        self.vm = None  # Vector Magnitudes

        # Details
        self.sample_rate = None
        self.starttime = None
        self.file_dur = None

        # RUNS METHODS
        self.import_file()

    def import_file(self):
        """Method that loads voltage channel, sample rate, starttime, and file duration.
        Creates timestamp for each data point."""

        t0 = datetime.now()

        print("\n" + "Importing {}...".format(self.filepath))

        file = pyedflib.EdfReader(self.filepath)

        self.sample_rate = file.getSampleFrequencies()[0]
        self.accel_sample_rate = file.getSampleFrequencies()[1]

        # READS IN ECG DATA ===========================================================================================
        print("Importing file ...".format(self.filepath))
        self.raw = file.readSignal(chn=0)

        if self.load_accel:
            self.x = file.readSignal(chn=1)
            self.y = file.readSignal(chn=2)
            self.z = file.readSignal(chn=3)

            # Calculates gravity-subtracted vector magnitude. Converts from mg to G
            # Negative values become zero
            self.vm = (np.sqrt(np.square(np.array([self.x, self.y, self.z])).sum(axis=0)) - 1000) / 1000
            self.vm[self.vm < 0] = 0

        print("ECG data import complete.")

        self.starttime = file.getStartdatetime()
        self.file_dur = round(file.getFileDuration() / 3600, 3)

        # Data filtering
        self.filtered = self.filter_signal(data=self.raw, low_f=self.low_f, high_f=self.high_f,
                                           f_type=self.f_type, sample_f=self.sample_rate, filter_order=self.f_order)

        # TIMESTAMP GENERATION ========================================================================================
        t0_stamp = datetime.now()

        print("\n" + "Creating timestamps...")

        # Timestamps
        end_time = self.starttime + timedelta(seconds=len(self.raw)/self.sample_rate)
        self.timestamps = np.asarray(pd.date_range(start=self.starttime, end=end_time, periods=len(self.raw)))
        self.epoch_timestamps = self.timestamps[::self.epoch_len * self.sample_rate]

        t1_stamp = datetime.now()
        stamp_time = (t1_stamp - t0_stamp).seconds
        print("Complete ({} seconds).".format(round(stamp_time, 2)))

        t1 = datetime.now()
        proc_time = (t1 - t0).seconds
        print("\n" + "Import complete ({} seconds).".format(round(proc_time, 2)))

    @staticmethod
    def filter_signal(data, f_type, low_f=None, high_f=None, sample_f=None, filter_order=2):
        """Function that creates bandpass filter to ECG data.

        Required arguments:
        -data: 3-column array with each column containing one accelerometer axis
        -type: "lowpass", "highpass" or "bandpass"
        -low_f, high_f: filter cut-offs, Hz
        -sample_f: sampling frequency, Hz
        -filter_order: order of filter; integer
        """

        nyquist_freq = 0.5 * sample_f

        if f_type == "lowpass":
            low = low_f / nyquist_freq
            b, a = butter(N=filter_order, Wn=low, btype="lowpass")
            # filtered_data = lfilter(b, a, data)
            filtered_data = filtfilt(b, a, x=data)

        if f_type == "highpass":
            high = high_f / nyquist_freq

            b, a = butter(N=filter_order, Wn=high, btype="highpass")
            # filtered_data = lfilter(b, a, data)
            filtered_data = filtfilt(b, a, x=data)

        if f_type == "bandpass":
            low = low_f / nyquist_freq
            high = high_f / nyquist_freq

            b, a = butter(N=filter_order, Wn=[low, high], btype="bandpass")
            # filtered_data = lfilter(b, a, data)
            filtered_data = filtfilt(b, a, x=data)

        return filtered_data


class ECG:

    def __init__(self, filepath=None, output_dir=None, epoch_len=15, load_accel=False, write_data=True,
                 filter_data=False, low_f=1, high_f=30, f_type="bandpass", f_order=2):
        """Class that creates instance of class Bittium and runs signal quality check on data.

            :arguments
            -filepath: full pathway to Bittium Faros .edf file
            -output_dir: full pathway to where you want data to be saved
            -epoch_len: window length (number of seconds) over which quality check algorithm is run
            -load_accel: boolean of whether to load accelerometer channels (not needed for quality check)
            -write_data: boolean of whether to write epoch-by-epoch validity results to .csv in output_dir

            -filter_data: boolean
            -low_f: low-end cutoff frequency for lowpass or bandpass filters
            -high_f: high-end cuttoff frequency for highpass or bandpass filters
            -f_type: "lowpass", "highpass", or "bandpass"
            -f_order: filter order, integer

        """

        print()
        print("============================================= ECG DATA ==============================================")

        self.filepath = filepath
        self.filename = self.filepath.split("/")[-1].split(".")[0]
        self.subjectID = self.filename.split("_")[2]
        self.output_dir = output_dir
        self.epoch_len = epoch_len
        self.write_data = write_data

        # Filtering deteails
        self.filter_data = filter_data
        self.low_f = low_f
        self.high_f = high_f
        self.f_type = f_type
        self.f_order = f_order

        # Accelerometer details
        self.load_accel = load_accel

        self.accel_sample_rate = 1
        self.accel_x = None
        self.accel_y = None
        self.accel_z = None
        self.accel_vm = None
        self.svm = []

        # Raw data
        self.ecg = Bittium(filepath=self.filepath, load_accel=self.load_accel,
                           filter_data=self.filter_data, low_f=self.low_f, high_f=self.high_f,
                           f_type=self.f_type, f_order=self.f_order)

        self.sample_rate = self.ecg.sample_rate
        self.accel_sample_rate = self.ecg.accel_sample_rate
        self.raw = self.ecg.raw
        self.filtered = self.ecg.filtered
        self.timestamps = self.ecg.timestamps
        self.epoch_timestamps = self.ecg.epoch_timestamps

        self.accel_x, self.accel_y, self.accel_z, self.accel_vm = self.ecg.x, self.ecg.y, self.ecg.z, self.ecg.vm

        del self.ecg

        if self.load_accel:
            self.epoch_accel()

        self.epoch_validity, self.epoch_hr, self.avg_voltage = self.check_quality()

        # List of epoched heart rates but any invalid epoch is marked as None instead of 0 (as is self.epoch_hr)
        self.valid_hr = [self.epoch_hr[i] if self.epoch_validity[i] == 0 else None for i in range(len(self.epoch_hr))]

        self.quality_report = self.generate_quality_report(write_report=self.write_data)
        print(self.quality_report)

        if self.write_data:
            df = pd.DataFrame(list(zip(self.epoch_timestamps,
                                       ["Invalid" if i == 1 else "Valid" for i in self.epoch_validity])),
                              columns=["Timestamp", "Validity"])

            df.to_csv(path_or_buf=self.output_dir + self.filename + "_EpochValidity.csv", sep=",")

    def epoch_accel(self):

        for i in range(0, len(self.accel_vm), int(self.accel_sample_rate * self.epoch_len)):

            if i + self.epoch_len * self.accel_sample_rate > len(self.accel_vm):
                break

            vm_sum = sum(self.accel_vm[i:i + self.epoch_len * self.accel_sample_rate])

            self.svm.append(round(vm_sum, 5))

    def check_quality(self):
        """Performs quality check using Orphanidou et al. (2015) algorithm that has been tweaked to factor in voltage
           range as well.

           This function runs a loop that creates object from the class CheckQuality for each epoch in the raw data.
        """

        print("\n" + "Running quality check with Orphanidou et al. (2015) algorithm...")

        t0 = datetime.now()

        validity_list = []
        epoch_hr = []
        avg_voltage = []

        bar = progressbar.ProgressBar(maxval=len(self.raw),
                                      widgets=[progressbar.Bar('>', '', '|'), ' ',
                                               progressbar.Percentage()])
        bar.start()

        for start_index in range(0, int(len(self.raw)), self.epoch_len*self.sample_rate):
            bar.update(start_index + 1)

            qc = CheckQuality(ecg_object=self, start_index=start_index, epoch_len=self.epoch_len)

            avg_voltage.append(qc.volt_range)

            if qc.valid_period:
                validity_list.append(0)
                epoch_hr.append(round(qc.hr, 2))
            if not qc.valid_period:
                validity_list.append(1)
                epoch_hr.append(0)

        bar.finish()

        t1 = datetime.now()
        proc_time = (t1 - t0).seconds
        print("\n" + "Quality check complete ({} seconds).".format(round(proc_time, 2)))

        return validity_list, epoch_hr, avg_voltage

    def generate_quality_report(self, write_report=True):
        """Calculates how much of the data was usable. Returns values in dictionary."""

        valid_epochs = self.epoch_validity.count(0)  # number of valid epochs
        invalid_epochs = self.epoch_validity.count(1)  # number of invalid epochs
        hours_lost = round(invalid_epochs / (60 / self.epoch_len) / 60, 2)  # hours of invalid data
        perc_valid = round(valid_epochs / len(self.epoch_validity) * 100, 1)  # percent of valid data
        perc_invalid = round(invalid_epochs / len(self.epoch_validity) * 100, 1)  # percent of invalid data

        quality_report = {"Invalid epochs": invalid_epochs, "Hours lost": hours_lost,
                          "Percent valid": perc_valid, "Percent invalid": perc_invalid}

        print("{}% of the data is valid.".format(round(100 - perc_invalid), 3))

        if write_report:
            df = pd.DataFrame(list(zip([i for i in quality_report.keys()],
                                       [i for i in quality_report.values()])),
                              columns=["Variable", "Value"])

            df.to_csv(path_or_buf=self.output_dir + self.filename + "_QualityReport.csv", sep=",")

        return quality_report


class CheckQuality:
    """Class method that implements the Orphanidou ECG signal quality assessment algorithm on raw ECG data.

       Orphanidou, C. et al. (2015). Signal-Quality Indices for the Electrocardiogram and Photoplethysmogram:
       Derivation and Applications to Wireless Monitoring. IEEE Journal of Biomedical and Health Informatics.
       19(3). 832-838.
    """

    def __init__(self, ecg_object, start_index, voltage_thresh=250, epoch_len=15):
        """Initialization method.

        :param
        -ecg_object: EcgData class instance created by ImportEDF script
        -random_data: runs algorithm on randomly-generated section of data; False by default.
                      Takes priority over start_index.
        -start_index: index for windowing data; 0 by default
        -epoch_len: window length in seconds over which algorithm is run; 15 seconds by default
        """

        self.voltage_thresh = voltage_thresh
        self.epoch_len = epoch_len
        self.fs = ecg_object.sample_rate
        self.start_index = start_index

        self.raw_data = ecg_object.raw[self.start_index:self.start_index+self.epoch_len*self.fs]
        self.filt_data = ecg_object.filtered[self.start_index:self.start_index+self.epoch_len*self.fs]
        self.index_list = np.arange(0, len(self.raw_data), self.epoch_len*self.fs)

        self.rule_check_dict = {"Valid Period": False,
                                "HR Valid": False, "HR": None,
                                "Max RR Interval Valid": False, "Max RR Interval": None,
                                "RR Ratio Valid": False, "RR Ratio": None,
                                "Voltage Range Valid": False, "Voltage Range": None,
                                "Correlation Valid": False, "Correlation": None}

        # prep_data parameters
        self.r_peaks = None
        self.removed_peak = []
        self.enough_beats = True
        self.hr = 0
        self.delta_rr = []
        self.removal_indexes = []
        self.rr_ratio = None
        self.volt_range = 0

        # apply_rules parameters
        self.valid_hr = None
        self.valid_rr = None
        self.valid_ratio = None
        self.valid_range = None
        self.valid_corr = None
        self.rules_passed = None

        # adaptive_filter parameters
        self.median_rr = None
        self.ecg_windowed = []
        self.average_qrs = None
        self.average_r = 0

        # calculate_correlation parameters
        self.beat_ppmc = []
        self.valid_period = None

        """RUNS METHODS"""
        # Peak detection and basic outcome measures
        self.prep_data()

        # Runs rules check if enough peaks found
        if self.enough_beats:
            self.adaptive_filter()
            self.calculate_correlation()
            self.apply_rules()

    def prep_data(self):
        """Function that:
        -Initializes ecgdetector class instance
        -Runs stationary wavelet transform peak detection
            -Implements 0.1-10Hz bandpass filter
            -DB3 wavelet transformation
            -Pan-Tompkins peak detection thresholding
        -Calculates RR intervals
        -Removes first peak if it is within median RR interval / 2 from start of window
        -Calculates average HR in the window
        -Determines if there are enough beats in the window to indicate a possible valid period
        """

        # Initializes Detectors class instance with sample rate
        detectors = Detectors(self.fs)

        # Runs peak detection on raw data ----------------------------------------------------------------------------
        # Uses ecgdetectors package -> stationary wavelet transformation + Pan-Tompkins peak detection algorithm
        self.r_peaks = detectors.swt_detector(unfiltered_ecg=self.filt_data)

        # Checks to see if there are enough potential peaks to correspond to correct HR range ------------------------
        # Requires number of beats in window that corresponds to ~40 bpm to continue
        # Prevents the math in the self.hr calculation from returning "valid" numbers with too few beats
        # i.e. 3 beats in 3 seconds (HR = 60bpm) but nothing detected for rest of epoch
        if len(self.r_peaks) >= np.floor(40/60*self.epoch_len):
            self.enough_beats = True

            n_beats = len(self.r_peaks)  # number of beats in window
            delta_t = (self.r_peaks[-1] - self.r_peaks[0]) / self.fs  # time between first and last beat, seconds
            self.hr = 60 * (n_beats-1) / delta_t  # average HR, bpm

        # Stops function if not enough peaks found to be a potential valid period
        # Threshold corresponds to number of beats in the window for a HR of 40 bpm
        if len(self.r_peaks) < np.floor(40/60*self.epoch_len):
            self.enough_beats = False
            self.valid_period = False
            return

        # Calculates RR intervals in seconds -------------------------------------------------------------------------
        for peak1, peak2 in zip(self.r_peaks[:], self.r_peaks[1:]):
            rr_interval = (peak2 - peak1) / self.fs
            self.delta_rr.append(rr_interval)

        # Approach 1: median RR characteristics ----------------------------------------------------------------------
        # Calculates median RR-interval in seconds
        median_rr = np.median(self.delta_rr)

        # Converts median_rr to samples
        self.median_rr = int(median_rr * self.fs)

        # Removes any peak too close to start/end of data section: affects windowing later on ------------------------
        # Peak removed if within median_rr/2 samples of start of window
        # Peak removed if within median_rr/2 samples of end of window
        for i, peak in enumerate(self.r_peaks):
            if peak < (self.median_rr/2 + 1) or (self.epoch_len*self.fs - peak) < (self.median_rr/2 + 1):
                self.removed_peak.append(self.r_peaks.pop(i))
                self.removal_indexes.append(i)

        # Removes RR intervals corresponding to
        if len(self.removal_indexes) != 0:
            self.delta_rr = [self.delta_rr[i] for i in range(len(self.r_peaks)) if i not in self.removal_indexes]

        # Calculates range of ECG voltage ----------------------------------------------------------------------------
        self.volt_range = max(self.raw_data) - min(self.raw_data)

    def adaptive_filter(self):
        """Method that runs an adaptive filter that generates the "average" QRS template for the window of data.

        - Calculates the median RR interval
        - Generates a sub-window around each peak, +/- RR interval/2 in width
        - Deletes the final beat sub-window if it is too close to end of data window
        - Calculates the "average" QRS template for the window
        """

        # Approach 1: calculates median RR-interval in seconds  -------------------------------------------------------
        # See previous method

        # Approach 2: takes a window around each detected R-peak of width peak +/- median_rr/2 ------------------------
        for peak in self.r_peaks:
            window = self.filt_data[peak - int(self.median_rr / 2):peak + int(self.median_rr / 2)]
            self.ecg_windowed.append(window)  # Adds window to list of windows

        # Approach 3: determine average QRS template ------------------------------------------------------------------
        self.ecg_windowed = np.asarray(self.ecg_windowed)[1:]  # Converts list to np.array; omits first empty array

        # Calculates "correct" length (samples) for each window (median_rr number of datapoints)
        correct_window_len = 2*int(self.median_rr/2)

        # Removes final beat's window if its peak is less than median_rr/2 samples from end of window
        # Fixes issues when calculating average_qrs waveform
        if len(self.ecg_windowed[-1]) != correct_window_len:
            self.removed_peak.append(self.r_peaks.pop(-1))
            self.ecg_windowed = self.ecg_windowed[:-2]

        # Calculates "average" heartbeat using windows around each peak
        try:
            self.average_qrs = np.mean(self.ecg_windowed, axis=0)
        except ValueError:
            print("Failed to calculate mean QRS template.")

    def calculate_correlation(self):
        """Method that runs a correlation analysis for each beat and the average QRS template.

        - Runs a Pearson correlation between each beat and the QRS template
        - Calculates the average individual beat Pearson correlation value
        - The period is deemed valid if the average correlation is >= 0.66, invalid is < 0.66
        """

        # Calculates correlation between each beat window and the average beat window --------------------------------
        for beat in self.ecg_windowed:
            r = stats.pearsonr(x=beat, y=self.average_qrs)
            self.beat_ppmc.append(abs(r[0]))

        self.average_r = float(np.mean(self.beat_ppmc))
        self.average_r = round(self.average_r, 3)

    def apply_rules(self):
        """First stage of algorithm. Checks data against three rules to determine if the window is potentially valid.
        -Rule 1: HR needs to be between 40 and 180bpm
        -Rule 2: no RR interval can be more than 3 seconds
        -Rule 3: the ratio of the longest to shortest RR interval is less than 2.2
        -Rule 4: the amplitude range of the raw ECG voltage must exceed n microV (approximate range for non-wear)
        -Rule 5: the average correlation coefficient between each beat and the "average" beat must exceed 0.66
        -Verdict: all rules need to be passed
        """

        # Rule 1: "The HR extrapolated from the sample must be between 40 and 180 bpm" -------------------------------
        if 40 <= self.hr <= 180:
            self.valid_hr = True
        else:
            self.valid_hr = False

        # Rule 2: "the maximum acceptable gap between successive R-peaks is 3s ---------------------------------------
        for rr_interval in self.delta_rr:
            if rr_interval < 3:
                self.valid_rr = True

            if rr_interval >= 3:
                self.valid_rr = False
                break

        # Rule 3: "the ratio of the maximum beat-to-beat interval to the minimum beat-to-beat interval... ------------
        # should be less than 2.5"
        self.rr_ratio = max(self.delta_rr) / min(self.delta_rr)

        if self.rr_ratio >= 2.5:
            self.valid_ratio = False

        if self.rr_ratio < 2.5:
            self.valid_ratio = True

        # Rule 4: the range of the raw ECG signal needs to be >= 250 microV ------------------------------------------
        if self.volt_range <= self.voltage_thresh:
            self.valid_range = False

        if self.volt_range > self.voltage_thresh:
            self.valid_range = True

        # Rule 5: Determines if average R value is above threshold of 0.66 -------------------------------------------
        if self.average_r >= 0.66:
            self.valid_corr = True

        if self.average_r < 0.66:
            self.valid_corr = False

        # FINAL VERDICT: valid period if all rules are passed --------------------------------------------------------
        if self.valid_hr and self.valid_rr and self.valid_ratio and self.valid_range and self.valid_corr:
            self.valid_period = True
        else:
            self.valid_period = False

        self.rule_check_dict = {"Valid Period": self.valid_period,
                                "HR Valid": self.valid_hr, "HR": round(self.hr, 1),
                                "Max RR Interval Valid": self.valid_rr, "Max RR Interval": round(max(self.delta_rr), 1),
                                "RR Ratio Valid": self.valid_ratio, "RR Ratio": round(self.rr_ratio, 1),
                                "Voltage Range Valid": self.valid_range, "Voltage Range": round(self.volt_range, 1),
                                "Correlation Valid": self.valid_corr, "Correlation": self.average_r}

"""
ecg = ECG(filepath="/Users/kyleweber/Desktop/Data/OND07/EDF/OND07_WTL_3028_01_BF.EDF",
          output_dir="/Users/kyleweber/Desktop/", epoch_len=15, load_accel=False, write_data=True,
          filter_data=True, low_f=1, high_f=30, f_type="bandpass")
"""