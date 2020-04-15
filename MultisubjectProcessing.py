import LocateUsableParticipants
from Subject import Subject
import pandas as pd
from statsmodels.stats.anova import AnovaRM
from statsmodels.stats.multicomp import (pairwise_tukeyhsd, MultiComparison)
import statsmodels.stats.power as smp
from matplotlib import pyplot as plt
import numpy as np
import scipy
import os
import seaborn as sns
import researchpy as rp
import statsmodels.api as sm
import statsmodels.stats.multicomp
from statsmodels.formula.api import ols
import pingouin as pg

usable_subjs = LocateUsableParticipants.SubjectSubset(check_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/"
                                                                 "OND07_ProcessingStatus.xlsx",
                                                      wrist_ankle=True, wrist_hr=False,
                                                      wrist_hracc=False, hr_hracc=False,
                                                      ankle_hr=False, ankle_hracc=False,
                                                      wrist_only=False, ankle_only=False,
                                                      hr_only=False, hracc_only=False,
                                                      require_treadmill=True, require_all=False)


def loop_subjects_standalone(subj_list):
    diff_list = []
    mean_abs_diff_list = []

    for subj in subj_list:
        try:
            x = Subject(
                # What data to load in
                subjectID=int(subj),
                load_ecg=True, load_ankle=True, load_wrist=True,
                load_raw_ecg=False, load_raw_ankle=False, load_raw_wrist=False,
                from_processed=True,

                # Model parameters
                rest_hr_window=30,
                n_epochs_rest_hr=30,
                hracc_threshold=25,
                filter_ecg=True,
                epoch_len=15,

                # Data files
                raw_edf_folder="/Users/kyleweber/Desktop/Data/OND07/EDF/",
                crop_index_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/CropIndexes_All.csv",
                treadmill_log_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Treadmill_Log.csv",
                demographics_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Demographics_Data.csv",
                sleeplog_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/SleepLogs_All.csv",
                output_dir="/Users/kyleweber/Desktop/Data/OND07/Processed Data/",
                processed_folder="/Users/kyleweber/Desktop/Data/OND07/Processed Data/Model Output/",
                write_results=False)

        except:
            usable_subjs.remove(str(subj))
            pass

        ind_data, group_data, difference_list, rms_diff, mean_abs_diff = x.valid_all.calculate_regression_diff()

        for d in difference_list:
            diff_list.append(d)
        mean_abs_diff_list.append(mean_abs_diff)

    return diff_list, mean_abs_diff_list


def histogram_ind_vs_group_speed_differences():
    """Generates a histogram that shows the difference in predicted gait speed between individual and group regression
       equations for all specified participants with 95%CI shaded.
       Also plots histogram of each participant's average absolute difference.
    """

    def loop_subjects(subj_list):
        diff_list = []
        mean_abs_diff_list = []

        for subj in subj_list:
            try:
                x = Subject(
                    # What data to load in
                    subjectID=int(subj),
                    load_ecg=True, load_ankle=True, load_wrist=False,
                    load_raw_ecg=False, load_raw_ankle=False, load_raw_wrist=False,
                    from_processed=True,

                    # Model parameters
                    rest_hr_window=30,
                    n_epochs_rest_hr=30,
                    hracc_threshold=30,
                    filter_ecg=True,
                    epoch_len=15,

                    # Data files
                    raw_edf_folder="/Users/kyleweber/Desktop/Data/OND07/EDF/",
                    crop_index_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/CropIndexes_All.csv",
                    treadmill_log_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Treadmill_Log.csv",
                    demographics_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Demographics_Data.csv",
                    sleeplog_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/SleepLogs_All.csv",
                    output_dir="/Users/kyleweber/Desktop/Data/OND07/Processed Data/",
                    processed_folder="/Users/kyleweber/Desktop/Data/OND07/Processed Data/Model Output/",
                    write_results=False)

            except:
                usable_subjs.remove(str(subj))
                pass

            ind_data, group_data, difference_list, rms_diff, mean_abs_diff = x.valid_all.calculate_regression_diff()

            for d in difference_list:
                diff_list.append(d)
            mean_abs_diff_list.append(mean_abs_diff)

        return diff_list, mean_abs_diff_list

    diff, mean_diff = loop_subjects(usable_subjs)

    # Calculates difference's 95%CI
    diff_sd = np.std(diff)
    t_crit = scipy.stats.t.ppf(0.95, len(diff)-1)
    ci_width = diff_sd * t_crit

    plt.subplots(1, 2, figsize=(10, 7))
    plt.suptitle("Predicted Gait Speed Comparison: Waking Hours Above Meaningful Threshold")

    # Histogram: epoch-by-epoch difference during waking/active hours for all participants
    plt.subplot(1, 2, 1)
    plt.fill_between(x=[np.mean(diff) - ci_width, np.mean(diff) + ci_width], y1=0, y2=100,
                     color='#1576DC', alpha=0.35,
                     label="95% CI ({} to {})".format(round(np.mean(diff) - ci_width, 3),
                                                      round(np.mean(diff) + ci_width, 3)))
    plt.ylim(0, max(plt.hist(diff, bins=np.arange(min(diff), max(diff), 0.05),
                             density=True, color='#1576DC', edgecolor='black', cumulative=False)[0])*1.1)
    plt.xlabel("Difference (m/s)")
    plt.ylabel("Percent of All Data")
    plt.legend()
    plt.title("Predicted Gait Speed (Individual - Group)")

    plt.subplot(1, 2, 2)
    plt.hist(mean_diff, bins=np.arange(0, 1, 0.025), color="#B81313", edgecolor='black')
    plt.xlim(0, max(mean_diff)*1.1)
    plt.ylabel("Number of participants")
    plt.xlabel("Difference (m/s)")
    plt.title("Mean Absolute Difference by Participant")


def cohenskappa_ind_vs_group():
    """Function that performs epoch-by-epoch intensity classification analysis on waking/active periods for all
       designated participants. Plots each participant's Cohen's Kappa value."""

    def loop_subjects(subj_list):
        kappa_list = []

        for subj in subj_list:
            try:
                x = Subject(
                    # What data to load in
                    subjectID=int(subj),
                    load_ecg=True, load_ankle=True, load_wrist=False,
                    load_raw_ecg=False, load_raw_ankle=False, load_raw_wrist=False,
                    from_processed=True,

                    # Model parameters
                    rest_hr_window=30,
                    n_epochs_rest_hr=30,
                    hracc_threshold=30,
                    filter_ecg=True,
                    epoch_len=15,

                    # Data files
                    raw_edf_folder="/Users/kyleweber/Desktop/Data/OND07/EDF/",
                    crop_index_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/CropIndexes_All.csv",
                    treadmill_log_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Treadmill_Log.csv",
                    demographics_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Demographics_Data.csv",
                    sleeplog_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/SleepLogs_All.csv",
                    output_dir="/Users/kyleweber/Desktop/Data/OND07/Processed Data/",
                    processed_folder="/Users/kyleweber/Desktop/Data/OND07/Processed Data/Model Output/",
                    write_results=False)

                kappa_list.append(x.stats.regression_kappa_all)

            except:
                usable_subjs.remove(str(subj))
                pass

        return kappa_list

    # Runs loop function
    kappas = loop_subjects(subj_list=usable_subjs)

    df = pd.DataFrame(zip(usable_subjs, kappas), columns=["Subj", "Kappa"])

    plt.scatter(df.sort_values(by="Kappa")["Subj"], df.sort_values(by="Kappa")["Kappa"], c='red')
    plt.axhline(y=df.describe()["Kappa"]["mean"],
                linestyle='dashed', color='black', label="Mean = {}".format(round(df.describe()["Kappa"]["mean"], 3)))
    plt.legend()
    plt.ylabel("Cohen's Kappa")
    plt.xlabel("Subject ID")
    plt.xticks(rotation=45)
    plt.title("Waking, Active Intensity Agreement")


class AnovaComparisonRegressionActivityMinutes:
    """Class that analyzes differences in total activity minutes calculated from individual and group regression
       equations. Uses values from all specified subjects. Performs one-way repeated measures ANOVA followed by
       Tukey post-hoc tests."""

    def __init__(self, subj_list=None):

        self.subj_list = subj_list
        self.ind_minutes = []
        self.group_minutes = []
        self.df = None
        self.df_long = None
        self.aov = None
        self.aov_results = None
        self.tukey = None

        """RUNS METHODS"""
        self.import_data()
        self.shape_data()
        self.run_anova()
        self.plot_means()

    def import_data(self):

        self.ind_minutes, self.group_minutes = self.loop_subjects()

    def loop_subjects(self):

        ind_minutes = []
        group_minutes = []

        for subj in self.subj_list:
            try:
                x = Subject(
                    # What data to load in
                    subjectID=int(subj),
                    load_ecg=True, load_ankle=True, load_wrist=False,
                    load_raw_ecg=False, load_raw_ankle=False, load_raw_wrist=False,
                    from_processed=True,

                    # Model parameters
                    rest_hr_window=30,
                    n_epochs_rest_hr=30,
                    hracc_threshold=25,
                    filter_ecg=True,
                    epoch_len=15,

                    # Data files
                    raw_edf_folder="/Users/kyleweber/Desktop/Data/OND07/EDF/",
                    crop_index_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/CropIndexes_All.csv",
                    treadmill_log_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Treadmill_Log.csv",
                    demographics_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Demographics_Data.csv",
                    sleeplog_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/SleepLogs_All.csv",
                    output_dir="/Users/kyleweber/Desktop/Data/OND07/Processed Data/",
                    processed_folder="/Users/kyleweber/Desktop/Data/OND07/Processed Data/Model Output/",
                    write_results=False)

                if x.demographics["Height"] < 125 or x.demographics["Weight"] < 40:
                    usable_subjs.remove(str(subj))
                    break

                ind_minutes.append([value for value in x.valid_all.ankle_totals.values()][3::2])
                group_minutes.append([value for value in x.valid_all.ankle_totals_group.values()][3::2])

            except:
                usable_subjs.remove(str(subj))
                pass

        return ind_minutes, group_minutes

    def shape_data(self):

        # Shaping dataframes
        ind = np.array(self.ind_minutes)
        group = np.array(self.group_minutes)
        combined = np.concatenate((ind, group), axis=1)

        self.df = pd.DataFrame(combined, columns=["IndLight", "IndModerate", "IndVigorous",
                                                  "GroupLight", "GroupModerate", "GroupVigorous"])
        self.df.insert(loc=0, column="ID", value=usable_subjs[:self.df.shape[0]])

        self.df_long = pd.melt(frame=self.df, id_vars="ID", var_name="Group", value_name="Minutes")

    def run_anova(self):

        self.aov = AnovaRM(self.df_long, depvar="Minutes", subject="ID", within=["Group"])
        self.aov_results = self.aov.fit()

        print("\n" + "======================================== MAIN EFFECTS ========================================")
        print("\n", self.aov_results.anova_table)

        self.tukey = "n.s."

        if self.aov_results.anova_table["Pr > F"][0] <= 0.05:
            print("")
            tukey_data = MultiComparison(self.df_long["Minutes"], self.df_long["Group"])
            self.tukey = tukey_data.tukeyhsd(alpha=0.05)
            print("============================================ POST HOC ===========================================")
            print("\n", self.tukey.summary())

    def plot_means(self):

        means = [self.df["IndLight"].describe()['mean'], self.df["GroupLight"].describe()['mean'],
                 self.df["IndModerate"].describe()['mean'], self.df["GroupModerate"].describe()['mean'],
                 self.df["IndVigorous"].describe()['mean'], self.df["GroupVigorous"].describe()['mean']]

        sd = [self.df["IndLight"].describe()['std'], self.df["GroupLight"].describe()['std'],
              self.df["IndModerate"].describe()['std'], self.df["GroupModerate"].describe()['std'],
              self.df["IndVigorous"].describe()['std'], self.df["GroupVigorous"].describe()['std']]

        plt.bar(["IndLight", "GroupLight", "IndMod", "GroupMod", "IndVig", "GroupVig"], means,
                color=('green', 'green', 'orange', 'orange', 'red', 'red'), edgecolor='black')

        # Standard error of the means error bars
        plt.errorbar(["IndLight", "GroupLight", "IndMod", "GroupMod", "IndVig", "GroupVig"], means,
                     [i/(len(self.df)**(1/2)) for i in sd],
                     linestyle="", color='black', capsize=4, capthick=1, barsabove=True)

        plt.ylabel("Minutes")
        plt.title("Means ± SEM")


class AverageAnkleCountsStratify:

    def __init__(self, subj_list=None, check_file=None, n_groups=4):
        """Calculates average ankle counts during waking/worn hours and during waking/worn/valid ECG hours.
           Performs power analysis to determine attained statistical power in separating groups by ankle counts.

           Purpose: to determine if these two ways of calculating average counts are the same. Affects how
           participants are stratified into relative activity level groups.

           :argument
           -subj_list: List of IDs to loop through if no check_file is given
           -check_file: pathway to spreadsheet containing ID, ankle counts and wrist count data
           -n_groups: number of groups to generate. The top and bottom n_total/n_group participants are split into
                      low-active and high-active groups
        """

        self.check_file = check_file
        self.avg_counts_accels = []
        self.avg_counts_validecg = []
        self.ids = []
        self.high_active_ids = None
        self.low_active_ids = None
        self.subj_list = subj_list
        self.n_groups = n_groups
        self.n_per_group = 1

        self.df = None  # Whole dataset
        self.low_active = None  # low activity group
        self.high_active = None  # high activity group

        # Stats data
        self.t_crit = 0
        self.r = None
        self.ttest_counts = None
        self.ttest_age = None
        self.ttest_height = None
        self.ttest_weight = None
        self.ttest_bmi = None
        self.wilcoxon_counts = None
        self.wilcoxon_age = None
        self.wilcoxon_weight = None
        self.wilcoxon_height = None
        self.wilcoxon_sex = None

        # Power analysis data
        self.cohens_d = 0
        self.power_object = None
        self.n_required = 0
        self.achieved_power = 0

        if os.path.exists(self.check_file):
            self.import_data()

        if not os.path.exists(self.check_file) or self.check_file is None:
            self.loop_participants(subj_list=subj_list)

        self.create_groups(n_groups=self.n_groups)
        self.create_group_lists()
        self.calculate_stats()

    def import_data(self):
        """Imports data from Excel sheet."""

        self.df = pd.read_excel(io=self.check_file,
                                columns=["Ankle Valid Counts", "Wrist Valid Counts", "Age", "Sex", "Weight", "Height"])

        self.df["BMI"] = self.df["Weight"] / ((self.df["Height"] / 100) ** 2)
        self.df.dropna(inplace=True)

        self.df = self.df.loc[self.df["ID"].isin(self.subj_list)]

    def loop_participants(self, subj_list):
        """Loops through all participants and calculates average ankle accelerometer counts from
           waking hours and waking hours with valid ECG.
        """

        for subj in subj_list:

            try:

                x = Subject(
                        # What data to load in
                        subjectID=subj,
                        load_ecg=False, load_ankle=True, load_wrist=True,
                        load_raw_ecg=False, load_raw_ankle=False, load_raw_wrist=False,
                        from_processed=True,

                        # Model parameters
                        rest_hr_window=30,
                        n_epochs_rest_hr=30,
                        hracc_threshold=30,
                        filter_ecg=True,
                        epoch_len=15,

                        # Data files
                        raw_edf_folder="/Users/kyleweber/Desktop/Data/OND07/EDF/",
                        crop_index_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/CropIndexes_All.csv",
                        treadmill_log_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Treadmill_Log.csv",
                        demographics_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Demographics_Data.csv",
                        sleeplog_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/SleepLogs_All.csv",
                        output_dir="/Users/kyleweber/Desktop/Data/OND07/Processed Data/",
                        processed_folder="/Users/kyleweber/Desktop/Data/OND07/Processed Data/Model Output/",
                        write_results=False)

                z = Subject(
                        # What data to load in
                        subjectID=subj,
                        load_ecg=True, load_ankle=True, load_wrist=True,
                        load_raw_ecg=False, load_raw_ankle=False, load_raw_wrist=False,
                        from_processed=True,

                        # Model parameters
                        rest_hr_window=30,
                        n_epochs_rest_hr=30,
                        hracc_threshold=30,
                        filter_ecg=True,
                        epoch_len=15,

                        # Data files
                        raw_edf_folder="/Users/kyleweber/Desktop/Data/OND07/EDF/",
                        crop_index_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/CropIndexes_All.csv",
                        treadmill_log_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Treadmill_Log.csv",
                        demographics_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Demographics_Data.csv",
                        sleeplog_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/SleepLogs_All.csv",
                        output_dir="/Users/kyleweber/Desktop/Data/OND07/Processed Data/",
                        processed_folder="/Users/kyleweber/Desktop/Data/OND07/Processed Data/Model Output/",
                        write_results=False)

                self.avg_counts_accels.append(x.valid_accelonly.avg_ankle_counts)
                self.avg_counts_validecg.append(z.valid_all.avg_ankle_counts)

                self.ids.append(x.subjectID)

            except:
                pass

            self.df = pd.DataFrame(list(zip(self.ids, self.avg_counts_accels, self.avg_counts_validecg)),
                                   columns=["ID", "All", "Valid ECG"])

    def create_groups(self, n_groups):

        self.n_per_group = int((self.df.shape[0] - self.df.shape[0] % n_groups) / n_groups)

        sorted_by_anklecounts = self.df.sort_values(["Ankle Valid Counts"])

        self.low_active = sorted_by_anklecounts.iloc[0:self.n_per_group]
        self.high_active = sorted_by_anklecounts.iloc[-self.n_per_group:]

        self.df = self.df.sort_values(["Ankle Valid Counts"])
        self.df["Group"] = ["Low" for i in range(self.n_per_group)] + ["High" for i in range(self.n_per_group)]

    def calculate_stats(self):
        """Pearson correlation between ankle and wrist counts, independent samples T-test, Wilcoxon signed rank test."""

        # COUNTS COMPARISON ------------------------------------------------------------------------------------------
        self.r = scipy.stats.pearsonr(self.df["Ankle Valid Counts"], self.df["Wrist Valid Counts"])
        print("\nCorrelation (ankle ~ wrist counts): r = {}, p = {}".format(round(self.r[0], 3), round(self.r[1], 3)))

        # BETWEEN-GROUP COMPARISONS ----------------------------------------------------------------------------------
        print("\n------------------------ Comparison between {} groups created using ankle counts"
              "------------------------ ".format(self.n_groups))

        self.t_crit = scipy.stats.t.ppf(0.05, df=self.n_per_group*2-2)

        # Ankle counts
        self.ttest_counts = scipy.stats.ttest_ind(self.low_active["Wrist Valid Counts"],
                                                  self.high_active["Wrist Valid Counts"])
        print("Independent T-tests:")
        print("-Counts: t = {}, p = {}".format(round(self.ttest_counts[0], 3), round(self.ttest_counts[1], 3)))

        # Consider one-sided
        self.wilcoxon_counts = scipy.stats.wilcoxon(self.low_active["Ankle Valid Counts"],
                                                    self.high_active["Ankle Valid Counts"])

        # Age
        self.ttest_age = scipy.stats.ttest_ind(self.low_active["Age"], self.high_active["Age"])
        print("-Age:    t = {}, p = {}".format(round(self.ttest_age[0], 3), round(self.ttest_age[1], 3)))

        # Weight
        self.ttest_weight = scipy.stats.ttest_ind(self.low_active["Weight"], self.high_active["Weight"])
        print("-Weight: t = {}, p = {}".format(round(self.ttest_weight[0], 3), round(self.ttest_weight[1], 3)))

        # Height
        self.ttest_height = scipy.stats.ttest_ind(self.low_active["Height"], self.high_active["Height"])
        print("-Height: t = {}, p = {}".format(round(self.ttest_height[0], 3), round(self.ttest_weight[1], 3)))

        self.ttest_bmi = scipy.stats.ttest_ind(self.low_active["BMI"], self.high_active["BMI"])
        print("-BMI: t = {}, p = {}".format(round(self.ttest_bmi[0], 3), round(self.ttest_bmi[1], 3)))

        # Sex
        group1_n_females = [i for i in self.low_active["Sex"].values].count(1)
        group2_n_females = [i for i in self.high_active["Sex"].values].count(1)

        print("\n-Females per group:")
        print("     -Low activity: {}".format(group1_n_females))
        print("     -High activity: {}".format(group2_n_females))

        # Effect size and statistical power ---------------------------------------------------------------------------
        sd1 = self.low_active.describe().values[2][0]
        mean1 = self.low_active.describe().values[1][0]
        sd2 = self.high_active.describe().values[2][0]
        mean2 = self.high_active.describe().values[1][0]

        pooled_sd = ((sd1 ** 2 + sd2 ** 2) / 2) ** (1 / 2)

        self.cohens_d = round((mean2 - mean1) / pooled_sd, 3)

        print("\nPOWER ANALYSIS")
        print("\n-Effect size between average ankle counts: d = {}".format(self.cohens_d))

        # Statistical power -------------------------------------------------------------------------------------------
        self.power_object = smp.TTestIndPower()
        self.n_required = self.power_object.solve_power(abs(self.cohens_d), power=0.8, alpha=0.05)
        self.achieved_power = smp.TTestIndPower().solve_power(self.cohens_d, nobs1=5, ratio=1, alpha=.05)

        print("-Sample size required to reach for β of 0.80 is {}.".format(round(self.n_required, 2)))
        print("-Attained power = {}".format(round(self.achieved_power, 3)))

        if self.achieved_power > 0.8:
            print("     -Acceptable power attained.")

    def plot_power(self):
        self.power_object.plot_power(dep_var="nobs", nobs=np.array(range(2, 20)), effect_size=np.array([self.cohens_d]))
        plt.scatter(self.n_per_group, self.achieved_power, c='black',
                    label="Power achieved ({})".format(round(self.achieved_power, 3)))
        plt.fill_between(x=np.array(range(3, 20)), y1=0.8, y2=0, color='red', alpha=0.25)
        plt.fill_between(x=np.array(range(3, 20)), y1=0.8, y2=1, color='green', alpha=0.25)

        plt.xlabel("N participants")
        plt.xticks(np.arange(2, 20, 2))
        plt.ylabel("Power")
        plt.legend()
        plt.title("Power Calculation")

    def show_boxplots(self):

        plt.subplots(2, 2, figsize=(10, 7))

        plt.subplot(2, 2, 1)
        plt.boxplot(x=[self.low_active["Ankle Valid Counts"], self.high_active["Ankle Valid Counts"]],
                    labels=["Low activity", "High activity"])
        plt.ylabel("Average Ankle Counts")
        plt.title("Ankle Counts")

        plt.subplot(2, 2, 2)
        plt.boxplot(x=[self.low_active["Age"], self.high_active["Age"]], labels=["Low activity", "High activity"])
        plt.ylabel("Age (years)")
        plt.title("Age")

        plt.subplot(2, 2, 3)
        plt.boxplot(x=[self.low_active["Height"], self.high_active["Height"]], labels=["Low activity", "High activity"])
        plt.ylabel("Height (cm)")
        plt.title("Height")

        plt.subplot(2, 2, 4)
        plt.boxplot(x=[self.low_active["Weight"], self.high_active["Weight"]], labels=["Low activity", "High activity"])
        plt.ylabel("Weight (kg)")
        plt.title("Weight")

    def create_group_lists(self):

        self.high_active_ids = self.df.loc[self.df["Group"] == "High"]["ID"].values
        self.low_active_ids = self.df.loc[self.df["Group"] == "Low"]["ID"].values


"""z = AverageAnkleCountsStratify(subj_list=usable_subjs.participant_list,
                               check_file="/Users/kyleweber/Desktop/Data/OND07/Processed Data/"
                                          "ECGValidity_AccelCounts_All.xlsx", n_groups=2)"""


class AverageAnkleCountsValidInvalid:

    def __init__(self, subj_list=None):
        """Calculates average counts during wear periods for both when ECG was valid and invalid.
           Purpose: to determine if movement influences the validity of ECG data.
        """

        self.valid_counts = []
        self.invalid_counts = []
        self.ids = []
        self.passed_ids = []
        self.subj_list = subj_list

        self.df = None
        self.ttest = None
        self.differences = None
        self.valid_higher = 0
        self.invalid_higher = 0
        self.no_diff = 0

        self.loop_participants(subj_list=subj_list)
        self.calculate_stats()
        self.plot_results()

    def loop_participants(self, subj_list):

        for subj in subj_list:

            try:

                z = Subject(
                        # What data to load in
                        subjectID=subj,
                        load_ecg=True, load_ankle=False, load_wrist=True,
                        load_raw_ecg=False, load_raw_ankle=False, load_raw_wrist=False,
                        from_processed=True,

                        # Model parameters
                        rest_hr_window=30,
                        n_epochs_rest_hr=30,
                        hracc_threshold=30,
                        filter_ecg=True,
                        epoch_len=15,

                        # Data files
                        raw_edf_folder="/Users/kyleweber/Desktop/Data/OND07/EDF/",
                        crop_index_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/CropIndexes_All.csv",
                        treadmill_log_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Treadmill_Log.csv",
                        demographics_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/Demographics_Data.csv",
                        sleeplog_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/SleepLogs_All.csv",
                        output_dir="/Users/kyleweber/Desktop/Data/OND07/Processed Data/",
                        processed_folder="/Users/kyleweber/Desktop/Data/OND07/Processed Data/Model Output/",
                        write_results=False)

                index_len = min([len(z.wrist.epoch.svm), len(z.ecg.epoch_validity), len(z.nonwear.status)])

                self.invalid_counts.append(np.asarray([z.wrist.epoch.svm[i] for i in range(index_len) if
                                                       z.ecg.epoch_validity[i] == 1 and
                                                       z.nonwear.status[i] == 0]).mean())
                self.valid_counts.append(np.asarray([z.wrist.epoch.svm[i] for i in range(index_len) if
                                                     z.ecg.epoch_validity[i] == 0 and
                                                     z.nonwear.status[i] == 0]).mean())

                self.ids.append(subj)

            except:
                self.passed_ids.append(subj)
                pass

        self.df = pd.DataFrame(list(zip(self.ids, self.invalid_counts, self.valid_counts)),
                               columns=["ID", "InvalidECG", "ValidECG"])

    def calculate_stats(self):

        self.ttest = scipy.stats.ttest_rel(self.df["InvalidECG"], self.df["ValidECG"])
        print("Paired T-Test: t = {}, p = {}".format(round(self.ttest[0], 3), round(self.ttest[1], 3)))

        self.differences = [invalid - valid for invalid, valid in zip(self.invalid_counts, self.valid_counts)]

        for diff in self.differences:
            if diff > 0:
                self.invalid_higher += 1
            if diff < 0:
                self.valid_higher += 1
            if diff == 0:
                self.no_diff += 1

    def plot_results(self):

        plt.title("Average Counts During Valid/Invalid ECG (p = {})".format(round(self.ttest[1], 3)))

        plt.scatter(self.df["ValidECG"], self.df["InvalidECG"], c='black', label="Data")
        plt.xlabel("Valid ECG")
        plt.ylabel("Invalid ECG")
        plt.plot(np.arange(0, 140), np.arange(0, 140), color='black', linestyle='dashed', label="y=x")
        plt.xlim(0, 140)
        plt.ylim(0, 140)

        plt.fill_between(x=[i for i in range(0, 140)],
                         y1=[i for i in range(0, 140)], y2=140,
                         color='red', alpha=0.25,
                         label="Higher during invalid ECG (n={})".format(self.invalid_higher))

        plt.fill_between(x=[i for i in range(0, 140)],
                         y1=0, y2=[i for i in range(0, 140)],
                         color='green', alpha=0.25,
                         label="Higher during valid ECG (n={})".format(self.valid_higher))
        plt.legend()


class RelativeActivityEffectDiff:

    def __init__(self, data_file):
        """Statistical analysis between relatively active and inactive groups for between-model differences in
           activity minutes.
        """

        self.data_file = data_file

        self.high_active_ids = [3024, 3029, 3031, 3032, 3043]
        self.low_active_ids = [3026, 3030, 3034, 3037, 3039]

        self.df = None
        self.norm_df_intensity = None
        self.norm_df_comparison = None

        """RUNS METHODS"""
        self.import_data()
        self.normalize_max_min()

    def import_data(self):

        self.df = pd.read_excel(self.data_file, index_col="ID")

    def normalize_max_min(self):
        col_names = ['SEDENTARY', 'LIGHT', 'MODERATE', 'VIGOROUS', 'SEDENTARY%', 'LIGHT%', 'MODERATE%', 'VIGOROUS%']

        self.norm_df_intensity = pd.DataFrame(columns=col_names)
        self.norm_df_comparison = pd.DataFrame(columns=col_names)

        # NORMALIZED BY INTENSITY -------------------------------------------------------------------------------------
        for subj in self.high_active_ids + self.low_active_ids:
            temp_df = self.df.loc[self.df.index.values == subj]
            temp_df["ID"] = [subj for i in range(6)]

            norm_subj_df = pd.DataFrame(temp_df["ID"])

            for col in col_names:
                min_val = min(temp_df[col])
                max_val = max(temp_df[col])

                norm_subj_df[col] = pd.DataFrame((temp_df[col] - min_val) / (max_val - min_val))

            self.norm_df_intensity = self.norm_df_intensity.append(norm_subj_df, ignore_index=True)

    def comparison_by_group_anova(self, dependent_var):
        """Performs a Group x Comparison mixed ANOVA on the dependent variable that is passed in.
           Performs pairwise T-test comparisons for post-hoc analysis.
           Plots group means using Seaborn package.

        :argument
        -dependent_var: name of column in self.df to use as dependent variable

        :returns
        -data objects from pingouin ANOVA and posthoc objects
        """

        print("\nPerforming Group x Comparison mixed ANOVA for"
              "dependent variable {}.".format(dependent_var.capitalize()))

        aov = pg.mixed_anova(dv=dependent_var, within="COMPARISON", between="GROUP", subject="ID", data=self.df)
        pg.print_table(aov.iloc[:, 0:8])
        print()
        pg.print_table(aov.iloc[:, 9:])

        sns.pointplot(data=self.df, x='GROUP', y=dependent_var, hue='COMPARISON',
                      dodge=False, markers='o', capsize=.1, errwidth=1, palette='Set1')
        plt.title("Group x Comparison Mixed ANOVA: {}".format(dependent_var.capitalize()))

        posthoc = pg.pairwise_ttests(dv=dependent_var, within="COMPARISON", between='GROUP',
                                     subject='ID', data=self.df)
        pg.print_table(posthoc)

        return aov, posthoc

    def group_by_intensity_anova(self, model_comparison, data_type="percent", use_normed=False):
        """Performs a Group x Intensity mixed ANOVA on the dependent variable that is passed in.
           Performs pairwise T-test comparisons for post-hoc analysis.
           Plots group means using Seaborn package.

        :argument
        -model_comparison: name of column in self.df to use as dependent variable
        -data_types: 'minutes' or 'percent'; type of data to use
        -use_norm: whether or not to use normed data

        :returns
        -data objects from pingouin ANOVA and posthoc objects
        """

        # DATA FORMATTING ---------------------------------------------------------------------------------------------
        if use_normed:
            df = self.norm_df
        if not use_normed:
            df = self.df

        # Pulls rows from self.df for desired model comparison
        comp_names = ["Wrist-Ankle", "Wrist-HR", "Wrist-HRAcc", "Ankle-HR", "Ankle-HRAcc", "HR-HRAcc"]
        row_int = comp_names.index(model_comparison)
        df2 = df.iloc[0::6]

        # df for minutes data
        mins_df = df2[["SEDENTARY", "LIGHT", "MODERATE", "VIGOROUS"]]

        # df for % data
        perc_df = df2[["SEDENTARY%", "LIGHT%", "MODERATE%", "VIGOROUS%"]]

        # Sets df to correct data type
        if data_type == "percent":
            df = perc_df
        if data_type == "minutes":
            df = mins_df

        df["ID"] = self.high_active_ids + self.low_active_ids

        # Creates column in df of IDs
        df_long = pd.melt(frame=df, id_vars="ID", var_name="INTENSITY", value_name="VALUE")

        high_list = ["HIGH" for i in range(5)]
        low_list = ["LOW" for i in range(5)]
        group_list = high_list + low_list
        df_long["GROUP"] = (group_list * 4)

        print(df_long)

        # DATA VISUALIZATION -----------------------------------------------------------------------------------------

        # Creates 2x1 subplots of group means
        plt.subplots(1, 2, figsize=(12, 7))
        plt.subplots_adjust(wspace=0.20)
        plt.suptitle("Group x Intensity Mixed ANOVA: {} "
                     "(normalized={})".format(model_comparison.capitalize(), use_normed))

        # Two activity level groups: one line for each intensity
        plt.subplot(1, 2, 1)
        sns.pointplot(data=df_long, x="GROUP", y="VALUE", hue="INTENSITY",
                      dodge=False, markers='o', capsize=.1, errwidth=1, palette='Set1')
        plt.ylabel("Difference ({})".format(data_type))
        plt.axhline(y=0, linestyle="dashed", color='black')

        # Four intensity groups: one line for each activity level group
        plt.subplot(1, 2, 2)
        sns.pointplot(data=df_long, x="INTENSITY", y="VALUE", hue="GROUP",
                      dodge=False, markers='o', capsize=.1, errwidth=1, palette='Set1')
        plt.ylabel("")
        plt.axhline(y=0, linestyle="dashed", color='black')

        # STATISTICAL ANALYSIS ---------------------------------------------------------------------------------------
        print("\nPerforming Group x Comparison mixed ANOVA using {} data "
              "for the {} model.".format(data_type, model_comparison))

        # Group x Intensity mixed ANOVA
        aov = pg.mixed_anova(dv="VALUE", within="INTENSITY", between="GROUP", subject="ID", data=df_long)
        pg.print_table(aov.iloc[:, 0:8])
        pg.print_table(aov.iloc[:, 9:])

        posthoc = pg.pairwise_ttests(dv="VALUE", within="INTENSITY", between='GROUP', subject='ID', data=df_long)
        pg.print_table(posthoc)

        return aov, posthoc


# x = RelativeActivityEffectDiff('/Users/kyleweber/Desktop/Data/OND07/Processed Data/'
#                               'Activity Level Comparison/ActivityGroupData_Differences.xlsx')
# x.norm_df_intensity["GROUP"] = x.df["GROUP"].values


class Objective2:

    def __init__(self, data_file='/Users/kyleweber/Desktop/Data/OND07/Processed Data/Kappas_AllData.xlsx'):

        os.chdir("/Users/kyleweber/Desktop/")

        self.data_file = data_file
        self.df = None
        self.oneway_rm_aov = None
        self.ttests_unpaired = None
        self.ttests_paired = None

        """RUNS METHODS"""
        self.load_data()
        self.pairwise_ttests_paired()
        self.pairwise_ttests_unpaired()

    def load_data(self):
        self.df = pd.read_excel(self.data_file)

    def check_normality(self):
        for col_name in self.df.keys():
            result = scipy.stats.shapiro(self.df[col_name].dropna())
            print(col_name, ":", "W =", round(result[0], 3), "p =", round(result[1], 3))

    def pairwise_ttests_unpaired(self):

        df = self.df.melt(id_vars="ID")

        self.ttests_unpaired = pg.pairwise_ttests(dv="value", subject='ID',
                                                  between='variable', data=df,
                                                  padjust="bonf", effsize="cohen", parametric=True)

    def pairwise_ttests_paired(self):

        df = self.df.melt(id_vars="ID")

        self.oneway_rm_aov = pg.rm_anova(data=df, dv="value", within="variable", subject='ID')

        self.ttests_paired = pg.pairwise_ttests(dv="value", subject='ID',
                                                within='variable', data=df,
                                                padjust="bonf", effsize="cohen", parametric=True)


# a = Objective2(data_file='/Users/kyleweber/Desktop/Data/OND07/Processed Data/Kappas_AllData.xlsx')
# b = Objective2(data_file='/Users/kyleweber/Desktop/Data/OND07/Processed Data/Kappas_RepeatedOnly.xlsx')


class Objective3:

    def __init__(self, activity_data_file=None, kappa_data_file=None):

        os.chdir("/Users/kyleweber/Desktop/")

        self.activity_data_file = activity_data_file
        self.kappa_data_file = kappa_data_file
        self.df_mins = None
        self.df_percent = None
        self.df_kappa = None
        self.df_kappa_long = None
        self.shapiro_df = None
        self.levene_df = None
        self.aov = None
        self.kappa_aov = None
        self.posthoc_para = None
        self.posthoc_nonpara = None
        self.kappa_posthoc = None

        """RUNS METHODS"""
        self.load_data()
        # self.check_assumptions()
        self.perform_kappa_anova()

    def load_data(self):

        # Activity Minutes/Percent
        df = pd.read_excel(self.activity_data_file)

        self.df_mins = df[["ID", 'Group', 'Model', 'Sedentary', 'Light', 'Moderate', 'Vigorous']]
        self.df_percent = df[["ID", 'Group', 'Model', 'Sedentary%', 'Light%', 'Moderate%', 'Vigorous%']]

        self.df_percent["MVPA%"] = self.df_percent["Moderate%"] + self.df_percent["Vigorous%"]

        # Cohen's Kappa data
        self.df_kappa = pd.read_excel(self.kappa_data_file)

    def check_assumptions(self, show_plots=False):
        """Runs Shapiro-Wilk and Levene's test for each group x model combination and prints results.
           Shows boxplots sorted by group and model"""

        print("\n============================== Checking ANOVA assumptions ==============================")

        # Results df
        shapiro_lists = []

        levene_lists = []

        # Data sorted by Group
        by_group = self.df_percent.groupby("Group")

        for group_name in ["HIGH", "LOW"]:
            for intensity in ["Sedentary%", "Light%", "Moderate%", "Vigorous%", "MVPA%"]:
                shapiro = scipy.stats.shapiro(by_group.get_group(group_name)[intensity])
                shapiro_lists.append({"SortIV": group_name, "Intensity": intensity,
                                      "W": shapiro[0], "p": shapiro[1], "Violation": shapiro[1] <= .05})

        for intensity in ["Sedentary%", "Light%", "Moderate%", "Vigorous%", "MVPA%"]:
            levene = scipy.stats.levene(by_group.get_group("HIGH")[intensity], by_group.get_group("LOW")[intensity])
            levene_lists.append({"SortIV": "Group", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

        # Data sorted by Model
        by_model = self.df_percent.groupby("Model")

        for model_name in ["Wrist", "Ankle", "HR", "HR-Acc"]:
            for intensity in ["Sedentary%", "Light%", "Moderate%", "Vigorous%", "MVPA%"]:
                result = scipy.stats.shapiro(by_model.get_group(model_name)[intensity])
                shapiro_lists.append({"SortIV": model_name, "Intensity": intensity,
                                      "W": result[0], "p": result[1], "Violation": result[1] <= .05})

        for intensity in ["Sedentary%", "Light%", "Moderate%", "Vigorous%", "MVPA%"]:
            levene = scipy.stats.levene(by_model.get_group("Wrist")[intensity], by_model.get_group("Ankle")[intensity])
            levene_lists.append({"SortIV": "Wrist-Ankle", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

            levene = scipy.stats.levene(by_model.get_group("Wrist")[intensity], by_model.get_group("HR")[intensity])
            levene_lists.append({"SortIV": "Wrist-HR", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

            levene = scipy.stats.levene(by_model.get_group("Wrist")[intensity], by_model.get_group("HR-Acc")[intensity])
            levene_lists.append({"SortIV": "Wrist-HRAcc", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

            levene = scipy.stats.levene(by_model.get_group("Ankle")[intensity], by_model.get_group("HR")[intensity])
            levene_lists.append({"SortIV": "Ankle-HR", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

            levene = scipy.stats.levene(by_model.get_group("Ankle")[intensity], by_model.get_group("HR-Acc")[intensity])
            levene_lists.append({"SortIV": "Ankle-HRAcc", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

            levene = scipy.stats.levene(by_model.get_group("HR")[intensity], by_model.get_group("HR-Acc")[intensity])
            levene_lists.append({"SortIV": "HR-HRAcc", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

        self.shapiro_df = pd.DataFrame(shapiro_lists, columns=["SortIV", "Intensity", "W", "p", "Violation"])
        self.levene_df = pd.DataFrame(levene_lists, columns=["SortIV", "Intensity", "W", "p", "Violation"])

        print("\nSHAPIRO-WILK TEST FOR NORMALITY\n")
        print(self.shapiro_df)

        print("\nLEVENE TEST FOR HOMOGENEITY OF VARIANCE\n")
        print(self.levene_df)

        if show_plots:
            by_group.boxplot(column=["Sedentary%", "Light%", "Moderate%", "Vigorous%"])
            by_model.boxplot(column=["Sedentary%", "Light%", "Moderate%", "Vigorous%"])

    def perform_activity_anova(self, activity_intensity="Moderate", data_type="percent"):

        if data_type == "percent":
            df = self.df_percent
            activity_intensity = activity_intensity + "%"
        if data_type == "minutes":
            df = self.df_mins

        # PLOTTING ---------------------------------------------------------------------------------------------------
        # Creates 2x1 subplots of group means
        plt.subplots(1, 2, figsize=(12, 7))
        plt.subplots_adjust(wspace=0.20)
        plt.suptitle("Group x Model Mixed ANOVA: {} Activity".format(activity_intensity))

        # Two activity level groups: one line for each intensity
        plt.subplot(1, 2, 1)
        sns.pointplot(data=df, x="Group", y=activity_intensity, hue="Model",
                      dodge=True, markers='o', capsize=.1, errwidth=1, palette='Set1')
        plt.ylabel("{}".format(data_type.capitalize()))

        # Four intensity groups: one line for each activity level group
        plt.subplot(1, 2, 2)
        sns.pointplot(data=df, x="Model", y=activity_intensity, hue="Group",
                      dodge=True, markers='o', capsize=.1, errwidth=1, palette='Set1')
        plt.ylabel("")

        # STATISTICAL ANALYSIS ---------------------------------------------------------------------------------------
        print("\nPerforming Group x Model mixed ANOVA on {} activity.".format(activity_intensity))

        # Group x Intensity mixed ANOVA
        self.aov = pg.mixed_anova(dv=activity_intensity, within="Model", between="Group", subject="ID", data=df,
                                  correction=True)
        pg.print_table(self.aov)

        group_p = self.aov.loc[self.aov["Source"] == "Group"]["p-unc"]
        group_sig = group_p.values[0] <= 0.05

        model_p = self.aov.loc[self.aov["Source"] == "Model"]["p-unc"]
        model_sig = model_p.values[0] <= 0.05

        interaction_p = self.aov.loc[self.aov["Source"] == "Interaction"]["p-unc"]
        interaction_sig = interaction_p.values[0] <= 0.05

        print("ANOVA quick summary:")
        if model_sig:
            print("-Main effect of Model (p = {})".format(round(model_p.values[0], 3)))
        if not model_sig:
            print("-No main effect of Model")
        if group_sig:
            print("-Main effect of Group (p = {})".format(round(group_p.values[0], 3)))
        if not group_sig:
            print("-No main effect of Group")
        if interaction_sig:
            print("-Signficiant Group x Model interaction (p = {})".format(round(interaction_p.values[0], 3)))
        if not interaction_sig:
            print("-No Group x Model interaction")

        posthoc_para = pg.pairwise_ttests(dv=activity_intensity, subject='ID',
                                          within="Model", between='Group',
                                          data=df,
                                          padjust="bonf", effsize="cohen", parametric=True)
        posthoc_nonpara = pg.pairwise_ttests(dv=activity_intensity, subject='ID',
                                             within="Model", between='Group',
                                             data=df,
                                             padjust="bonf", effsize="cohen", parametric=False)

        self.posthoc_para = posthoc_para
        self.posthoc_nonpara = posthoc_nonpara
        pg.print_table(posthoc_para)
        pg.print_table(posthoc_nonpara)

    def plot_main_effects(self, intensity):

        if intensity[-1] != "%":
            intensity += "%"

        plt.subplots(3, 1, figsize=(12, 7))
        plt.suptitle("{} Activity".format(intensity.capitalize()))

        plt.subplot(1, 3, 1)
        model_means = rp.summary_cont(self.df_percent.groupby(['Model']))[intensity.capitalize()]["Mean"]
        model_sd = rp.summary_cont(self.df_percent.groupby(['Model']))[intensity.capitalize()]["SD"]
        plt.bar([i for i in model_sd.index], [100 * i for i in model_means.values],
                yerr=[i * 100 for i in model_sd], capsize=10, ecolor='black',
                color=["Red", "Blue", "Green", "Purple"], edgecolor='black', linewidth=2)
        plt.ylabel("% of Collection")
        plt.title("Model Means")

        plt.subplot(1, 3, 2)
        group_means = rp.summary_cont(self.df_percent.groupby(['Group']))[intensity.capitalize()]["Mean"]
        group_sd = rp.summary_cont(self.df_percent.groupby(['Group']))[intensity.capitalize()]["SD"]
        plt.bar([i for i in group_means.index], [100 * i for i in group_means.values],
                yerr=[i * 100 for i in group_sd], capsize=10, ecolor='black',
                color=["Grey", "White"], edgecolor='black', linewidth=2)
        plt.title("Group Means")

        plt.subplot(1, 3, 3)
        sns.pointplot(data=x.df_percent, x="Model", y=intensity.capitalize(), hue="Group",
                      dodge=True, markers='o', capsize=.1, errwidth=1, palette='Set1')
        plt.title("All Combination Means")
        plt.ylabel(" ")

    def perform_kappa_anova(self):

        # MIXED ANOVA  ------------------------------------------------------------------------------------------------
        print("\nPerforming Group x Comparison mixed ANOVA on Cohen's Kappa values.")

        # Group x Intensity mixed ANOVA
        self.df_kappa_long = self.df_kappa.melt(id_vars=('ID', "Group"), var_name="Comparison", value_name="Kappa")

        self.kappa_aov = pg.mixed_anova(dv="Kappa", within="Comparison", between="Group", subject="ID",
                                        data=self.df_kappa_long, correction=True)
        pg.print_table(self.kappa_aov)

        # POST HOC ----------------------------------------------------------------------------------------------------
        self.kappa_posthoc = pg.pairwise_ttests(dv="Kappa", subject='ID', within="Comparison", between='Group',
                                                data=self.df_kappa_long,
                                                padjust="bonf", effsize="cohen", parametric=True)

    def plot_mains_effects_kappa(self):

        plt.subplots(3, 1, figsize=(12, 7))
        plt.suptitle("Cohen's Kappas (mean ± SD; n=10)")
        plt.subplots_adjust(wspace=0.25)

        plt.subplot(1, 3, 1)
        comp_means = rp.summary_cont(self.df_kappa_long.groupby(['Comparison']))["Kappa"]["Mean"]
        comp_sd = rp.summary_cont(self.df_kappa_long.groupby(['Comparison']))["Kappa"]["SD"]

        plt.bar([i for i in comp_means.index], [i for i in comp_means.values],
                yerr=[i for i in comp_sd], capsize=8, ecolor='black',
                color=['purple', 'orange', 'red', 'yellow', 'blue', 'green'], edgecolor='black', linewidth=2)
        plt.ylabel("Kappa")
        plt.title("Model Comparison")
        plt.yticks(np.arange(0, 1.1, 0.1))
        plt.xticks(fontsize=8, rotation=45)
        plt.yticks(fontsize=10)

        plt.subplot(1, 3, 2)
        group_means = rp.summary_cont(self.df_kappa_long.groupby(['Group']))["Kappa"]["Mean"]
        group_sd = rp.summary_cont(self.df_kappa_long.groupby(['Group']))["Kappa"]["SD"]

        plt.bar([i for i in group_sd.index], [i for i in group_means.values],
                yerr=[i for i in group_sd], capsize=10, ecolor='black',
                color=["lightgrey", "dimgrey"], alpha=0.5, edgecolor='black', linewidth=2)
        plt.title("Activity Group")
        plt.xlabel("Activity Level")
        plt.yticks(np.arange(0, 1.1, 0.1))
        plt.xticks(fontsize=8, rotation=45)
        plt.yticks(fontsize=10)

        plt.subplot(1, 3, 3)
        sns.pointplot(data=self.df_kappa_long, x="Group", y="Kappa", hue="Comparison",
                      dodge=False, markers='o', capsize=.1, errwidth=1, palette='Set1')
        plt.title("Interaction")
        plt.xticks(fontsize=8, rotation=45)
        plt.yticks(np.arange(0, 1.1, 0.1))
        plt.yticks(fontsize=10)
        plt.ylabel(" ")
        plt.xlabel("Activity Level")


"""x = Objective3(activity_data_file='/Users/kyleweber/Desktop/Data/OND07/Processed Data/Activity Level Comparison/'
                                  'ActivityGroupsData_AllActivityMinutes.xlsx',
               kappa_data_file='/Users/kyleweber/Desktop/Data/OND07/Processed Data/Kappas_RepeatedOnly.xlsx')"""


class Objective1:

    def __init__(self, activity_data_file='/Users/kyleweber/Desktop/Data/OND07/Processed Data/'
                                          'Activity Level Comparison/ActivityGroupsData_AllActivityMinutes.xlsx',
                 intensity=None):

        os.chdir("/Users/kyleweber/Desktop/")

        self.activity_data_file = activity_data_file
        self.intensity = intensity
        self.df_percent = None
        self.shapiro_df = None
        self.levene_df = None
        self.aov = None
        self.posthoc = None

        """RUNS METHODS"""
        self.load_data()
        self.perform_anova(intensity=self.intensity)

    def load_data(self):

        # Activity Minutes/Percent
        df = pd.read_excel(self.activity_data_file)

        self.df_percent = df[["ID", 'Group', 'Model', 'Sedentary%', 'Light%', 'Moderate%', 'Vigorous%']]

        self.df_percent["MVPA%"] = self.df_percent["Moderate%"] + self.df_percent["Vigorous%"]

    def check_assumptions(self, show_plots=False):

        shapiro_lists = []
        levene_lists = []
        by_model = self.df_percent.groupby("Model")

        for model_name in ["Ankle", "Wrist", "HR", "HR-Acc"]:
            for intensity in ["Sedentary%", "Light%", "Moderate%", "Vigorous%", "MVPA%"]:
                result = scipy.stats.shapiro(by_model.get_group(model_name)[intensity])
                shapiro_lists.append({"Model": model_name, "Intensity": intensity,
                                      "W": result[0], "p": result[1], "Violation": result[1] <= .05})

        self.shapiro_df = pd.DataFrame(shapiro_lists, columns=["Model", "Intensity", "W", "p", "Violation"])

        for intensity in ["Sedentary%", "Light%", "Moderate%", "Vigorous%", "MVPA%"]:
            levene = scipy.stats.levene(by_model.get_group("Wrist")[intensity], by_model.get_group("Ankle")[intensity])
            levene_lists.append({"SortIV": "Wrist-Ankle", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

            levene = scipy.stats.levene(by_model.get_group("Wrist")[intensity], by_model.get_group("HR")[intensity])
            levene_lists.append({"SortIV": "Wrist-HR", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

            levene = scipy.stats.levene(by_model.get_group("Wrist")[intensity], by_model.get_group("HR-Acc")[intensity])
            levene_lists.append({"SortIV": "Wrist-HRAcc", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

            levene = scipy.stats.levene(by_model.get_group("Ankle")[intensity], by_model.get_group("HR")[intensity])
            levene_lists.append({"SortIV": "Ankle-HR", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

            levene = scipy.stats.levene(by_model.get_group("Ankle")[intensity], by_model.get_group("HR-Acc")[intensity])
            levene_lists.append({"SortIV": "Ankle-HRAcc", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

            levene = scipy.stats.levene(by_model.get_group("HR")[intensity], by_model.get_group("HR-Acc")[intensity])
            levene_lists.append({"SortIV": "HR-HRAcc", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

        self.levene_df = pd.DataFrame(levene_lists, columns=["SortIV", "Intensity", "W", "p", "Violation"])

        if show_plots:
            by_model.boxplot(column=["Sedentary%", "Light%", "Moderate%", "Vigorous%", "MVPA%"])

    def perform_anova(self, intensity):
        self.aov = pg.rm_anova(data=self.df_percent, dv=intensity, within="Model", subject="ID", correction=True,
                               detailed=True)
        print(self.aov)

        self.posthoc = pg.pairwise_ttests(dv=intensity, subject='ID', within="Model",
                                          data=self.df_percent,
                                          padjust="bonf", effsize="cohen", parametric=True)
        print(self.posthoc)

    def plot_main_effects(self):

        plt.subplots(2, 2, figsize=(12, 7))
        plt.subplots_adjust(hspace=.30)

        plt.suptitle("Effect of Model on Total Activity")

        plt.subplot(2, 2, 1)
        model_means = rp.summary_cont(self.df_percent.groupby(['Model']))["Sedentary%"]["Mean"]
        model_sd = rp.summary_cont(self.df_percent.groupby(['Model']))["Sedentary%"]["SD"]
        plt.bar([i for i in model_sd.index], [100 * i for i in model_means.values],
                yerr=[i * 100 for i in model_sd], capsize=10, ecolor='black',
                color=["Red", "Blue", "Green", "Purple"], edgecolor='black', linewidth=2)
        plt.ylabel("% of Collection")
        plt.title("Sedentary")

        plt.subplot(2, 2, 2)
        model_means = rp.summary_cont(self.df_percent.groupby(['Model']))["Light%"]["Mean"]
        model_sd = rp.summary_cont(self.df_percent.groupby(['Model']))["Light%"]["SD"]
        plt.bar([i for i in model_sd.index], [100 * i for i in model_means.values],
                yerr=[i * 100 for i in model_sd], capsize=10, ecolor='black',
                color=["Red", "Blue", "Green", "Purple"], edgecolor='black', linewidth=2)
        plt.ylabel(" ")
        plt.title("Light")

        plt.subplot(2, 2, 3)
        model_means = rp.summary_cont(self.df_percent.groupby(['Model']))["Moderate%"]["Mean"]
        model_sd = rp.summary_cont(self.df_percent.groupby(['Model']))["Moderate%"]["SD"]
        plt.bar([i for i in model_sd.index], [100 * i for i in model_means.values],
                yerr=[i * 100 for i in model_sd], capsize=10, ecolor='black',
                color=["Red", "Blue", "Green", "Purple"], edgecolor='black', linewidth=2)
        plt.ylabel("% of Collection")
        plt.title("Moderate")

        plt.subplot(2, 2, 4)
        model_means = rp.summary_cont(self.df_percent.groupby(['Model']))["Vigorous%"]["Mean"]
        model_sd = rp.summary_cont(self.df_percent.groupby(['Model']))["Vigorous%"]["SD"]
        plt.bar([i for i in model_sd.index], [100 * i for i in model_means.values],
                yerr=[i * 100 for i in model_sd], capsize=10, ecolor='black',
                color=["Red", "Blue", "Green", "Purple"], edgecolor='black', linewidth=2)
        plt.ylabel(" ")
        plt.title("Vigorous")

x = Objective1(intensity="MVPA%")
x.plot_main_effects()