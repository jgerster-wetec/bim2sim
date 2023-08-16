import json
import math
from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt
import matplotlib.dates as mdates

from bim2sim.plugins.PluginComfort.bim2sim_comfort.task import \
    ComfortVisualization
from bim2sim.plugins.PluginEnergyPlus.bim2sim_energyplus.utils import \
    PostprocessingUtils

EXPORT_PATH = r'C:\Users\Richter_lokal\sciebo\03-Paperdrafts' \
              r'\MDPI_SpecialIssue_Comfort_Climate\sim_results'

PLOT_PATH = Path(r'C:\Users\Richter_lokal\sciebo\03-Paperdrafts'
                 r'\MDPI_SpecialIssue_Comfort_Climate\img\generated_plots')
PMV_COLORS = ['#4d0080', '#0232c2', '#028cc2', '#03ffff',
              '#02c248', '#bbc202', '#c27f02', '#c22802']  # set 8 colors
CONSTRUCTION = 'heavy_'  # heavy_ or light_


def round_up_to_nearest_100(num):
    return math.ceil(num / 100) * 100


def floor_to_nearest_100(num):
    return math.floor(num / 100) * 100


def compare_sim_results(df1, df2, ylabel='', filter_min=0, filter_max=365,
                        mean_only=False):
    filtered_df1 = df1[(df1.index.dayofyear >= filter_min)
                       & (df1.index.dayofyear <= filter_max)]
    filtered_df2 = df2[(df2.index.dayofyear >= filter_min)
                       & (df2.index.dayofyear <= filter_max)]
    mean_df1 = filtered_df1.resample('D').mean()
    mean_df2 = filtered_df2.resample('D').mean()
    for col in df1:
        middle_of_day = mean_df1.index + pd.DateOffset(hours=12)

        plt.figure(figsize=(10, 6))
        if not mean_only:
            plt.plot(filtered_df1.index, filtered_df1[col], label='2015',
                     linewidth=0.5)
            plt.plot(filtered_df2.index, filtered_df2[col], label='2045',
                     linewidth=0.5)
        plt.plot(middle_of_day, mean_df1[col],
                 label='2015 (24h mean)',
                 linewidth=0.5)
        plt.plot(middle_of_day, mean_df2[col],
                 label='2045 (24h mean)',
                 linewidth=0.5)
        if filter_max - filter_min > 125:
            date_fmt = mdates.DateFormatter('%B')
        else:
            date_fmt = mdates.DateFormatter('%B %d')
        plt.gca().xaxis.set_major_formatter(date_fmt)
        plt.xlabel('Timestamp')
        plt.ylabel(ylabel)
        plt.title(col)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()


def barplot_per_column(df, title='', y_lim=[0, 7200], save_as=''):
    result = df.transpose()
    legend_colors = PMV_COLORS

    ax = result.plot(kind='bar', figsize=(10, 6), color=legend_colors)
    plt.title(title)
    plt.ylim(y_lim)
    plt.ylabel('hours')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    plt.xticks(rotation=90, ha='center')
    plt.tight_layout()
    plt.legend(title='PMV',
               prop={'size': 8})
    if save_as:
        plt.savefig(PLOT_PATH / str(CONSTRUCTION + save_as + '.png'))
    plt.show()



def evaluate_pmv_hours(pmv_df):
    bins = [-float('inf'), -3, -2, -1, 0, 1, 2, 3, float('inf')]
    labels = ['< -3', '-3 to -2', '-2 to -1', '-1 to 0',
              '0 to 1', '1 to 2', '2 to 3', '> 3']

    # Count the values in each bin for each column
    result = pd.DataFrame()

    for column in pmv_df.columns:
        counts, _ = pd.cut(pmv_df[column], bins=bins,
                           labels=labels,
                           right=False, include_lowest=True, retbins=True)
        counts = pd.Categorical(counts, categories=labels, ordered=True)
        result[column] = counts.value_counts()
    return result


def rename_duplicates(dictionary):
    value_counts = {}
    renamed_dict = {}
    for key, value in dictionary.items():
        if value in value_counts:
            value_counts[value] += 1
            new_value = f"{value}_{value_counts[value]}"
        else:
            value_counts[value] = 1
            new_value = value

        renamed_dict[key] = new_value
    return renamed_dict


def replace_partial_identifier(col, rename_dict):
    for identifier_part, new_name in rename_dict.items():
        if identifier_part.upper() in col:
            org_column = col
            return org_column, col.replace(identifier_part.upper(),
                                                new_name)
    return col, col




if __name__ == '__main__':
    zone_usage_path = EXPORT_PATH+fr'\{CONSTRUCTION}2015\export\zone_dict.json'
    with open(zone_usage_path) as json_file:
        zone_usage = json.load(json_file)
    rename_keys = {'Kitchen in non-residential buildings': 'Kitchen',
                   'WC and sanitary rooms in non-residential buildings':
                       'Bathroom',
                       }
    for key in zone_usage.keys():
        for key2 in rename_keys.keys():
            if zone_usage[key] == key2:
                zone_usage[key] = rename_keys[key2]

    zone_usage = rename_duplicates(zone_usage)

    df_ep_res15 = pd.read_csv(EXPORT_PATH +
                              fr'\{CONSTRUCTION}2015\export\EP-results'
                              r'\eplusout.csv')

    df_ep_res45 = pd.read_csv(EXPORT_PATH +
                              fr'\{CONSTRUCTION}2045\export\EP-results'
                              r'\eplusout.csv')

    for column in df_ep_res15.columns:
        column, new_name = replace_partial_identifier(column, zone_usage)
        df_ep_res15 = df_ep_res15.rename(columns={column: new_name})
    for column in df_ep_res45.columns:
        column, new_name = replace_partial_identifier(column, zone_usage)
        df_ep_res45 = df_ep_res45.rename(columns={column: new_name})

    # convert to date time index
    df_ep_res15["Date/Time"] = df_ep_res15["Date/Time"].apply(
        PostprocessingUtils._string_to_datetime)
    df_ep_res45["Date/Time"] = df_ep_res45["Date/Time"].apply(
        PostprocessingUtils._string_to_datetime)

    pmv_temp_df15 = df_ep_res15[[col for col in df_ep_res15.columns
                                 if 'Fanger Model PMV' in col]]
    pmv_temp_df15 = pmv_temp_df15.set_index(df_ep_res15['Date/Time'])
    pmv_temp_df45 = df_ep_res45[[col for col in df_ep_res45.columns
                                 if 'Fanger Model PMV' in col]]
    pmv_temp_df45 = pmv_temp_df45.set_index(df_ep_res15['Date/Time'])

    pmv_temp_df15.columns = pmv_temp_df15.columns.map(lambda x: x.removesuffix(
        ':Zone Thermal Comfort Fanger Model PMV [](Hourly)'))
    pmv_temp_df45.columns = pmv_temp_df45.columns.map(lambda x: x.removesuffix(
        ':Zone Thermal Comfort Fanger Model PMV [](Hourly)'))

    ppd_temp_df15 = df_ep_res15[[col for col in df_ep_res15.columns
                                 if 'Fanger Model PPD' in col]]

    ppd_temp_df15 = ppd_temp_df15.set_index(df_ep_res15['Date/Time'])
    ppd_temp_df45 = df_ep_res45[[col for col in df_ep_res45.columns
                                 if 'Fanger Model PPD' in col]]
    ppd_temp_df45 = ppd_temp_df45.set_index(df_ep_res15['Date/Time'])

    ppd_diff = ppd_temp_df45 - ppd_temp_df15

    pmv_temp_df15_hours = evaluate_pmv_hours(pmv_temp_df15)
    pmv_temp_df45_hours = evaluate_pmv_hours(pmv_temp_df45)
    ylim_max = round_up_to_nearest_100(max(pmv_temp_df15_hours.values.max(),
                                           pmv_temp_df45_hours.values.max()))

    barplot_per_column(pmv_temp_df15_hours, '2015', y_lim=[0, ylim_max],
                       save_as='pmv_df15_hours')
    barplot_per_column(pmv_temp_df45_hours, '2045', y_lim=[0, ylim_max],
                       save_as='pmv_df45_hours')

    pmv_hours_diff = pmv_temp_df45_hours-pmv_temp_df15_hours
    ylim_diff_max = round_up_to_nearest_100(pmv_hours_diff.values.max())
    ylim_diff_min = floor_to_nearest_100(pmv_hours_diff.values.min())
    barplot_per_column(pmv_hours_diff, 'Difference between 2015 and 2045',
                       y_lim=[ylim_diff_min, ylim_diff_max],
                       save_as='pmv_hours_diff')

    compare_sim_results(pmv_temp_df15, pmv_temp_df45, 'PMV', filter_min=0,
                        filter_max=365, mean_only=True)


    for col in ppd_diff:
        ComfortVisualization.visualize_calendar(pd.DataFrame(ppd_diff[col]))

    fig = plt.figure(figsize=(10,10))
    for i in range(len(ppd_diff.columns)):
        plt.scatter(df_ep_res45[df_ep_res45.columns[1]], df_ep_res45[
            ppd_diff.columns[i]], marker='.', s=(72./fig.dpi),
                    label=ppd_diff.columns[i])
    plt.legend()
    plt.show()


