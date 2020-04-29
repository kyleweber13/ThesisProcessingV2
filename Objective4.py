import LocateUsableParticipants
import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
import scipy
import os
import seaborn as sns
import researchpy as rp
import pingouin as pg

"""usable_subjs = LocateUsableParticipants.SubjectSubset(check_file="/Users/kyleweber/Desktop/Data/OND07/Tabular Data/"
                                                                 "OND07_ProcessingStatus.xlsx",
                                                      wrist_ankle=False, wrist_hr=False,
                                                      wrist_hracc=False, hr_hracc=False,
                                                      ankle_hr=False, ankle_hracc=False,
                                                      wrist_only=False, ankle_only=False,
                                                      hr_only=False, hracc_only=False,
                                                      require_treadmill=True, require_all=True)"""


class Objective4:

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
        self.kappa_shapiro_df = None
        self.kappa_levene_df = None
        self.descriptive_stats_activity = None
        self.descriptive_stats_kappa = None
        self.aov = None
        self.kappa_ttest = None
        self.kappa_wilcoxon = None
        self.posthoc_para = None
        self.posthoc_nonpara = None

        self.shapiro_results = None
        self.levene_results = None
        self.anova_results = None
        self.posthoc_results = None

        """RUNS METHODS"""
        self.load_data()
        self.check_assumptions()

    def load_data(self):

        # Activity Minutes/Percent ------------------------------------------------------------------------------------
        df = pd.read_excel(self.activity_data_file)

        self.df_mins = df[["ID", 'Group', 'Model', 'Sedentary', 'Light', 'Moderate', 'Vigorous']]
        self.df_percent = df[["ID", 'Group', 'Model', 'Sedentary%', 'Light%', 'Moderate%', 'Vigorous%']]

        self.df_percent["MVPA%"] = self.df_percent["Moderate%"] + self.df_percent["Vigorous%"]

        model_d = self.df_percent.groupby("Model").describe()
        group_d = self.df_percent.groupby("Group").describe()

        group_d = pd.concat([group_d, model_d])

        self.descriptive_stats_activity = pd.DataFrame(list(zip(["HIGH", "LOW", "Ankle", "Wrist"],
                                                                group_d["Sedentary%"]["mean"],
                                                                group_d["Sedentary%"]["std"],
                                                                group_d["Light%"]["mean"],
                                                                group_d["Light%"]["std"],
                                                                group_d["Moderate%"]["mean"],
                                                                group_d["Moderate%"]["std"],
                                                                group_d["Vigorous%"]["mean"],
                                                                group_d["Vigorous%"]["std"],
                                                                group_d["MVPA%"]["mean"],
                                                                group_d["MVPA%"]["std"])),
                                                       columns=["IV", "Sedentary_mean", "Sedentary_sd",
                                                                "Light_mean", "Light_sd",
                                                                "Moderate_mean", "Moderate_sd",
                                                                "Vigorous_mean", "Vigorous_sd",
                                                                "MVPA_mean", "MVPA_sd"])

        # Cohen's Kappa data -----------------------------------------------------------------------------------------
        self.df_kappa = pd.read_excel(self.kappa_data_file, sheet_name="Data")
        self.df_kappa_long = self.df_kappa.melt(id_vars=('ID', "Group"), var_name="Comparison", value_name="Kappa")

        comp_d = self.df_kappa_long.groupby("Comparison").describe()
        group_d = self.df_kappa_long.groupby("Group").describe()

        group_d = pd.concat([group_d, comp_d])

        self.descriptive_stats_kappa = pd.DataFrame(list(zip(["HIGH", "LOW", "Ankle-HR", "Ankle-HRAcc", "Ankle-Wrist",
                                                              "HR-HRAcc", "Wrist-HR", "Wrist-HRAcc"],
                                                             group_d["Kappa"]["mean"], group_d["Kappa"]["std"])),
                                                    columns=["IV", "Kappa_mean", "Kappa_sd"])

    def check_assumptions(self, show_plots=False):
        """Runs Shapiro-Wilk and Levene's test for each group x model combination and prints results.
           Shows boxplots sorted by group and model"""

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

        for model_name in ["Wrist", "HR"]:
            for intensity in ["Sedentary%", "Light%", "Moderate%", "Vigorous%", "MVPA%"]:
                result = scipy.stats.shapiro(by_model.get_group(model_name)[intensity])
                shapiro_lists.append({"SortIV": model_name, "Intensity": intensity,
                                      "W": result[0], "p": result[1], "Violation": result[1] <= .05})

        for intensity in ["Sedentary%", "Light%", "Moderate%", "Vigorous%", "MVPA%"]:
            levene = scipy.stats.levene(by_model.get_group("Wrist")[intensity], by_model.get_group("HR")[intensity])
            levene_lists.append({"SortIV": "Wrist-Ankle", "Intensity": intensity,
                                 "W": levene[0], "p": levene[1], "Violation": levene[1] <= .05})

        self.shapiro_df = pd.DataFrame(shapiro_lists, columns=["SortIV", "Intensity", "W", "p", "Violation"])
        self.levene_df = pd.DataFrame(levene_lists, columns=["SortIV", "Intensity", "W", "p", "Violation"])

        if show_plots:
            by_group.boxplot(column=["Sedentary%", "Light%", "Moderate%", "Vigorous%"])
            by_model.boxplot(column=["Sedentary%", "Light%", "Moderate%", "Vigorous%"])

    def perform_activity_anova(self, activity_intensity, data_type="percent"):

        if data_type == "percent":
            df = self.df_percent
            activity_intensity = activity_intensity + "%"
        if data_type == "minutes":
            df = self.df_mins

        # PLOTTING ---------------------------------------------------------------------------------------------------
        # Creates 2x1 subplots of group means
        plt.title("Group x Model Mixed ANOVA: {} Activity".format(activity_intensity))

        # Two activity level groups: one line for each intensity
        sns.pointplot(data=df, x="Group", y=activity_intensity, hue="Model",
                      dodge=False, markers='o', capsize=.1, errwidth=1, palette='Set1')
        plt.ylabel("{}".format(data_type.capitalize()))

        # STATISTICAL ANALYSIS ---------------------------------------------------------------------------------------
        print("\nPerforming Group x Model mixed ANOVA on {} activity.".format(activity_intensity))

        # Group x Intensity mixed ANOVA
        self.aov = pg.mixed_anova(dv=activity_intensity, within="Model", between="Group", subject="ID", data=df,
                                  correction='auto')
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
                                             padjust="bonf", effsize="hedges", parametric=False)

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
        model_means = rp.summary_cont(self.df_percent.groupby(['Model']))[intensity]["Mean"]
        model_sd = rp.summary_cont(self.df_percent.groupby(['Model']))[intensity]["SD"]
        plt.bar([i for i in model_sd.index], [100 * i for i in model_means.values],
                yerr=[i * 100 for i in model_sd], capsize=10, ecolor='black',
                color=["Red", "Blue", "Green", "Purple"], edgecolor='black', linewidth=2)
        plt.ylabel("% of Collection")
        plt.title("Model Means")

        plt.subplot(1, 3, 2)
        group_means = rp.summary_cont(self.df_percent.groupby(['Group']))[intensity]["Mean"]
        group_sd = rp.summary_cont(self.df_percent.groupby(['Group']))[intensity]["SD"]
        plt.bar([i for i in group_means.index], [100 * i for i in group_means.values],
                yerr=[i * 100 for i in group_sd], capsize=10, ecolor='black',
                color=["Grey", "White"], edgecolor='black', linewidth=2)
        plt.title("Group Means")

        plt.subplot(1, 3, 3)
        sns.pointplot(data=x.df_percent, x="Model", y=intensity, hue="Group",
                      dodge=True, markers='o', capsize=.1, errwidth=1, palette='Set1')
        plt.title("All Combination Means")
        plt.ylabel(" ")

    def check_kappa_assumptions(self, show_plots=False):
        """Runs Shapiro-Wilk and Levene's test for each group x model combination and prints results.
           Shows boxplots sorted by group and model"""

        print("\n============================== Checking normality for Kappa groups... ==============================")

        high = self.df_kappa_long.groupby("Group").get_group("HIGH")["Kappa"]
        low = self.df_kappa_long.groupby("Group").get_group("LOW")["Kappa"]

        high_shapiro = scipy.stats.shapiro(high)
        low_shapiro = scipy.stats.shapiro(low)

        print("High activity group: W = {}, p = {}".format(round(high_shapiro[0], 3), round(high_shapiro[1], 3)))
        print("Low activity group: W = {}, p = {}".format(round(low_shapiro[0], 3), round(low_shapiro[1], 3)))

    def perform_kappa_ttest(self):

        # MIXED ANOVA  ------------------------------------------------------------------------------------------------
        print("\nPerforming unpaired T-test between activity groups on Cohen's Kappa values.")

        high = self.df_kappa_long.groupby("Group").get_group("HIGH")["Kappa"]
        low = self.df_kappa_long.groupby("Group").get_group("LOW")["Kappa"]

        self.kappa_ttest = pg.ttest(high, low, paired=False, correction='auto')

        # Approximates hedges g using d x (1 - (3 / (4*(n1 + n2) - 9))
        self.kappa_ttest["hedges-g"] = self.kappa_ttest["cohen-d"] * (1 - (3 / (4 * 2*high.shape[0] - 9)))
        print(self.kappa_ttest)

        self.kappa_wilcoxon = pg.wilcoxon(high, low)
        print(self.kappa_wilcoxon)

    def plot_mains_effects_kappa(self):

        group_means = rp.summary_cont(self.df_kappa_long.groupby(['Group']))["Kappa"]["Mean"]
        group_sd = rp.summary_cont(self.df_kappa_long.groupby(['Group']))["Kappa"]["SD"]

        plt.bar([i for i in group_sd.index], [i for i in group_means.values],
                yerr=[i for i in group_sd], capsize=10, ecolor='black',
                color=["lightgrey", "dimgrey"], alpha=0.5, edgecolor='black', linewidth=2)
        plt.title("Activity Group Comparison: t = {}, p = {}".format(self.kappa_ttest["T"][0],
                                                                     round(self.kappa_ttest["p-val"][0], 3)))

        plt.ylabel("Kappa")
        plt.yticks(np.arange(0, 1.1, 0.1))
        plt.xticks(fontsize=8, rotation=45)
        plt.yticks(fontsize=10)

    def create_output_files(self, write_files=True):

        # NORMALITY CHECK ---------------------------------------------------------------------------------------------
        data = self.shapiro_df.loc[self.shapiro_df["SortIV"] == "HIGH"][["W", "p"]]
        high_list = ["HIGH", data.iloc[0][0], data.iloc[0][1], data.iloc[1][0], data.iloc[1][1],
                     data.iloc[2][0], data.iloc[2][1],
                     data.iloc[3][0], data.iloc[3][1], data.iloc[4][0], data.iloc[4][1]]

        data = self.shapiro_df.loc[self.shapiro_df["SortIV"] == "LOW"][["W", "p"]]
        low_list = ["LOW", data.iloc[0][0], data.iloc[0][1], data.iloc[1][0], data.iloc[1][1],
                    data.iloc[2][0], data.iloc[2][1],
                    data.iloc[3][0], data.iloc[3][1], data.iloc[4][0], data.iloc[4][1]]

        data = self.shapiro_df.loc[self.shapiro_df["SortIV"] == "Wrist"][["W", "p"]]
        wrist_list = ["Wrist", data.iloc[0][0], data.iloc[0][1], data.iloc[1][0], data.iloc[1][1],
                      data.iloc[2][0], data.iloc[2][1],
                      data.iloc[3][0], data.iloc[3][1], data.iloc[4][0], data.iloc[4][1]]

        data = self.shapiro_df.loc[self.shapiro_df["SortIV"] == "HR"][["W", "p"]]
        hr_list = ["HR", data.iloc[0][0], data.iloc[0][1], data.iloc[1][0], data.iloc[1][1], data.iloc[2][0],
                   data.iloc[2][1],
                   data.iloc[3][0], data.iloc[3][1], data.iloc[4][0], data.iloc[4][1]]

        self.shapiro_results = pd.DataFrame(list(zip(high_list, low_list, wrist_list, hr_list))).transpose()

        # SPHERICITY CHECK --------------------------------------------------------------------------------------------
        data = self.levene_df.loc[self.levene_df["SortIV"] == "Group"][["W", "p"]]
        group_list = ["Group", data.iloc[0][0], data.iloc[0][1], data.iloc[1][0], data.iloc[1][1],
                      data.iloc[2][0], data.iloc[2][1],
                      data.iloc[3][0], data.iloc[3][1], data.iloc[4][0], data.iloc[4][1]]

        try:
            data = self.levene_df.loc[self.levene_df["SortIV"] == "Wrist-Ankle"][["W", "p"]]
        except IndexError:
            data = self.levene_df.loc[self.levene_df["SortIV"] == "Wrist-HR"][["W", "p"]]

        model_list = ["Model", data.iloc[0][0], data.iloc[0][1], data.iloc[1][0], data.iloc[1][1],
                      data.iloc[2][0], data.iloc[2][1],
                      data.iloc[3][0], data.iloc[3][1], data.iloc[4][0], data.iloc[4][1]]

        self.levene_results = pd.DataFrame(list(zip(group_list, model_list))).transpose()

        # ANOVA -------------------------------------------------------------------------------------------------------
        self.perform_activity_anova("Sedentary")
        self.create_post_hoc_file(intensity="Sedentary", write_file=write_files)

        sed_group = ["Sed Group", self.aov.iloc[0, 2], self.aov.iloc[0, 3], self.aov.iloc[0, 5],
                     self.aov.iloc[0, 6], self.aov.iloc[0, 7]]
        sed_model = ["Sed Model", self.aov.iloc[1, 2], self.aov.iloc[1, 3], self.aov.iloc[1, 5],
                     self.aov.iloc[1, 6], self.aov.iloc[1, 7]]
        sed_inter = ["Sed Inter", self.aov.iloc[2, 2], self.aov.iloc[2, 3], self.aov.iloc[2, 5],
                     self.aov.iloc[2, 6], self.aov.iloc[2, 7]]

        self.perform_activity_anova("Light")
        self.create_post_hoc_file(intensity="Light", write_file=write_files)

        light_group = ["Light Group", self.aov.iloc[0, 2], self.aov.iloc[0, 3], self.aov.iloc[0, 5],
                       self.aov.iloc[0, 6], self.aov.iloc[0, 7]]
        light_model = ["Light Model", self.aov.iloc[1, 2], self.aov.iloc[1, 3], self.aov.iloc[1, 5],
                       self.aov.iloc[1, 6], self.aov.iloc[1, 7]]
        light_inter = ["Light Inter", self.aov.iloc[2, 2], self.aov.iloc[2, 3], self.aov.iloc[2, 5],
                       self.aov.iloc[2, 6], self.aov.iloc[2, 7]]

        self.perform_activity_anova("Moderate")
        self.create_post_hoc_file(intensity="Moderate", write_file=write_files)

        mod_group = ["Mod Group", self.aov.iloc[0, 2], self.aov.iloc[0, 3], self.aov.iloc[0, 5],
                     self.aov.iloc[0, 6], self.aov.iloc[0, 7]]
        mod_model = ["Mod Model", self.aov.iloc[1, 2], self.aov.iloc[1, 3], self.aov.iloc[1, 5],
                     self.aov.iloc[1, 6], self.aov.iloc[1, 7]]
        mod_inter = ["Mod Inter", self.aov.iloc[2, 2], self.aov.iloc[2, 3], self.aov.iloc[2, 5],
                     self.aov.iloc[2, 6], self.aov.iloc[2, 7]]

        self.perform_activity_anova("Vigorous")
        self.create_post_hoc_file(intensity="Vigorous", write_file=write_files)

        vig_group = ["Vig Group", self.aov.iloc[0, 2], self.aov.iloc[0, 3], self.aov.iloc[0, 5],
                     self.aov.iloc[0, 6], self.aov.iloc[0, 7]]
        vig_model = ["Vig Model", self.aov.iloc[1, 2], self.aov.iloc[1, 3], self.aov.iloc[1, 5],
                     self.aov.iloc[1, 6], self.aov.iloc[1, 7]]
        vig_inter = ["Vig Inter", self.aov.iloc[2, 2], self.aov.iloc[2, 3], self.aov.iloc[2, 5],
                     self.aov.iloc[2, 6], self.aov.iloc[2, 7]]

        self.perform_activity_anova("MVPA")
        self.create_post_hoc_file(intensity="MVPA", write_file=write_files)

        mvpa_group = ["MVPA Group", self.aov.iloc[0, 2], self.aov.iloc[0, 3], self.aov.iloc[0, 5],
                      self.aov.iloc[0, 6], self.aov.iloc[0, 7]]
        mvpa_model = ["MVPA Model", self.aov.iloc[1, 2], self.aov.iloc[1, 3], self.aov.iloc[1, 5],
                      self.aov.iloc[1, 6], self.aov.iloc[1, 7]]
        mvpa_inter = ["MVPA Inter", self.aov.iloc[2, 2], self.aov.iloc[2, 3], self.aov.iloc[2, 5],
                      self.aov.iloc[2, 6], self.aov.iloc[2, 7]]

        self.anova_results = pd.DataFrame(list(zip(sed_group, sed_model, sed_inter,
                                                   light_group, light_model, light_inter,
                                                   mod_group, mod_model, mod_inter,
                                                   vig_group, vig_model, vig_inter,
                                                   mvpa_group, mvpa_model, mvpa_inter))).transpose()
        self.anova_results.columns = ["Data", "DF", "DFerror", "F", "p_uncorr", "np2"]

        if write_files:
            self.shapiro_results.to_excel("4a_Shapiro.xlsx")
            self.levene_results.to_excel("4a_Levene.xlsx")
            self.anova_results.to_excel("4a_ANOVA.xlsx")

    def create_post_hoc_file(self, intensity, write_file=False):

        para = [i for i in self.posthoc_para.iloc[0].values][6:]
        nonpara = [i for i in self.posthoc_nonpara.iloc[0].values][6:]
        nonpara.pop(2)
        model_combined = para + nonpara
        model_combined.insert(0, model_combined.pop(2))
        model_combined.insert(-1, model_combined.pop(7))
        model_combined.pop(11)

        para = [i for i in self.posthoc_para.iloc[1].values][6:]
        nonpara = [i for i in self.posthoc_nonpara.iloc[1].values][6:]
        nonpara.pop(2)
        group_combined = para + nonpara
        group_combined.insert(0, group_combined.pop(2))
        group_combined.insert(-1, group_combined.pop(7))
        group_combined.pop(11)

        para = [i for i in self.posthoc_para.iloc[2].values][6:]
        nonpara = [i for i in self.posthoc_nonpara.iloc[2].values][6:]
        nonpara.pop(2)
        int1 = para + nonpara
        int1.insert(0, int1.pop(2))
        int1.insert(-1, int1.pop(7))
        int1.pop(11)

        para = [i for i in self.posthoc_para.iloc[3].values][6:]
        nonpara = [i for i in self.posthoc_nonpara.iloc[3].values][6:]
        nonpara.pop(2)
        int2 = para + nonpara
        int2.insert(0, int2.pop(2))
        int2.insert(-1, int2.pop(7))
        int2.pop(11)

        self.posthoc_results = pd.DataFrame(list(zip(model_combined, group_combined, int1, int2))).transpose()
        self.posthoc_results.columns = ["Tail", "T", "dof", "p-unc", "p-corr", "p_adj", "BF10",
                                        "U-val", "W-val", "p-unc", "p-corr", "Cohen's D", "Hedges' g"]

        if write_file:
            self.posthoc_results.to_excel("4a_{}_PostHoc.xlsx".format(intensity))


x = Objective4(activity_data_file='/Users/kyleweber/Desktop/Data/OND07/Processed Data/'
                                  'Activity and Kappa Data/ActivityGroupsData_WristHRActivityMinutes.xlsx',
               kappa_data_file='/Users/kyleweber/Desktop/Data/OND07/Processed Data/'
                               'Activity and Kappa Data/Kappa - WristHR.xlsx')

x.check_kappa_assumptions(False)
x.perform_kappa_ttest()
# x.check_assumptions(True)
# x.perform_activity_anova(activity_intensity="MVPA", data_type="percent")

x.create_output_files(write_files=True)