import csv
import json
import os
import re
import sys
from pathlib import Path
from zipfile import ZipFile
from collections import defaultdict

from tqdm import tqdm

category_mapping = {}
try:
    input_file = sys.argv[1]
except IndexError:
    input_file = 'input-example.csv'

mappings = open('mappings.txt')
pattern = re.compile(r'(.*)=\[(.*(?:,)?)\]')

for line in mappings:
    for (tag, names) in re.findall(pattern, line):
        category_mapping.update({
            tag: [i.strip() for i in names.split(',')]
        })

with open(input_file, newline='') as csvfile:
    rows = csv.DictReader(csvfile)
    rows = [row for row in rows]

    filtered_output = defaultdict(dict)
    for row in tqdm(rows, desc='Processing rows'):
        found = False
        for key, value in category_mapping.items():
            for v in value:
                if v.lower() in row['Payee'].lower() or v.lower() in row['Category'].lower():
                    category = key
                    filtered_output.setdefault(category, dict()).setdefault('data', list()).append(row)
                    found = True
                    break
            if found:
                break
        if not found:
            filtered_output.setdefault('Others', dict()).setdefault('data', list()).append(row)

    columns = list(list(rows)[0].keys())
    # print('## Columns ##')
    # print('\n'.join(columns))
    # print(json.dumps(filtered_output, indent=4, sort_keys=True))
    # print('\n')
    for category, value in filtered_output.items():
        total = sum([float(v['Amount (EUR)']) for v in value['data']])
        filtered_output[category].setdefault('total', round(total, 2))
        print("%s -> %.2f" % (category, total))

#print([row['Payee'] for row in filtered_output.get('Others', dict()).get('data', [])])

f = open("digest.js", "w")
f.write('data = %s' % json.dumps(dict(filtered_output), indent=4, sort_keys=True))
f.close()


def getListOfFiles(dirName):
    # create a list of file and sub directories
    # names in the given directory
    listOfFile = os.listdir(dirName)
    allFiles = list()
    # Iterate over all the entries
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        # If entry is a directory then get the list of files in this directory
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)

    return allFiles


def exportZIP(zipName, files):
    print("Output zip => digested/%s/%s.zip" % (zipName, zipName))
    if not os.path.exists('digested'):
        os.mkdir('digested')
    with ZipFile("digested/%s/%s.zip" % (zipName, zipName), 'w') as zipFile:
        for file in files:
            zipFile.write(file)


def exportFolder(folder_name, files):
    print("Output folder => digested/%s/" % folder_name)
    if not os.path.exists('digested'):
        os.mkdir('digested')

    if not os.path.exists('digested/%s' % folder_name):
        os.mkdir('digested/%s' % folder_name)

    for file in files:
        os.popen('cp -R %s %s' % (file, "digested/%s" % folder_name))


def exportPlotPie(filtered_list):
    import matplotlib.pyplot as plt
    import pandas as pd
    import numpy as np
    import seaborn as sns

    digest = [[dict(a, **{'Family': k}) for a in v['data']] for k, v in filtered_list.items()]
    flat_list = [item for sublist in digest for item in sublist]

    dfe = pd.DataFrame.from_dict(flat_list)
    dfe['Amount (EUR)'] = dfe['Amount (EUR)'].astype(np.float)

    pie_df = dfe[(dfe['Amount (EUR)'] < 0)]
    #pie_df = dfe
    pie_df = pie_df.groupby(['Family'])['Amount (EUR)'].sum().reset_index()
    pie_df = pie_df.set_index(['Family'])
    pie_df['Amount (EUR)'] = pie_df['Amount (EUR)'].map(abs)

    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return '{p:.2f}%  ({v:.2f} \u20AC)'.format(p=pct, v=val)

        return my_autopct

    def make_labels(data_frame):
        return list(map(lambda t: "%s - \u20AC%.2f" % t, list(zip(data_frame.index.values, data_frame['Amount (EUR)'].values))))

    ## Expenses ##
    make_labels(pie_df)
    pie_plot = pie_df.plot.pie(y='Amount (EUR)', figsize=(8, 8), autopct=make_autopct(pie_df['Amount (EUR)'].values))
    pie_plot.legend(make_labels(pie_df))
    dfe['Date'] = pd.to_datetime(dfe['Date'])
    dates = dfe['Date'].dt.strftime('%Y-%m-%d').sort_values().unique()
    pie_plot.set_title('Expenses for the period %s - %s' % (dates[0], dates[-1]))
    pie_plot.get_figure().savefig('digest_files/resources/TotalPie.png')
    plt.close()

    ## Income Outcome Chart ##
    pie_total = pd.DataFrame()
    pie_total['Category'] = dfe['Amount (EUR)'].map(lambda x: 'Income' if x > 0 else 'Outcome')
    pie_total['Amount (EUR)'] = dfe['Amount (EUR)']
    pie_total['Amount (EUR)'] = pie_total['Amount (EUR)'].map(abs)
    pie_total = pie_total.groupby(['Category'])['Amount (EUR)'].sum().reset_index()

    def remaming(income, outcome):
        return income - outcome

    inc_total = pie_total[pie_total['Category'].isin(['Income'])]['Amount (EUR)'].values[0]
    out_total = pie_total[pie_total['Category'].isin(['Outcome'])]['Amount (EUR)'].values[0]
    pie_total = pie_total.append({'Category': 'Remaining', 'Amount (EUR)': remaming(inc_total, out_total)}, ignore_index=True)
    pie_total = pie_total.set_index('Category')

    total_plot = pie_total.plot.pie(y='Amount (EUR)', figsize=(8, 8), autopct=make_autopct(pie_total['Amount (EUR)'].values))
    total_plot.set_title('Income/Outcome for the period %s - %s' % (dates[0], dates[-1]))
    total_plot.get_figure().savefig('digest_files/resources/IncomeOutcomePie.png')
    plt.close()

    for family in tqdm(set(dfe['Family'].values), desc="Plotting graphs"):
        plt.subplots_adjust(bottom=0.2)
        ### BAR PLOT ###
        import datetime
        dfe['Date'] = pd.to_datetime(dfe['Date'])
        # dfx = dfe[(dfe['Date'].isin(pd.date_range('2019-01-01', '2019-02-01')))]
        dfx = dfe[dfe['Family'].isin([family])]
        # dfgb = dfx.groupby(['Date','Family'])['Amount (EUR)'].sum().reset_index()

        concat = lambda x: "\n".join(x)

        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            dfx['Count'] = pd.to_numeric(1)

        dfxa = dfx.groupby(['Date']).agg({'Payee': concat, 'Amount (EUR)': 'sum', 'Count': 'sum'}).reset_index()
        bar_plot = sns.barplot(x='Date', y='Amount (EUR)', data=dfxa)

        for i, row in dfxa.iterrows():
            # print("%s, %s" % (i, row['Payment reference']))
            bar_plot.text(i, row['Amount (EUR)'],
                          "\u20AC %.2f - %s (%i)" % (row['Amount (EUR)'], row['Payee'][0:30], row['Count']), color='black',
                          ha="center", rotation=90)

        dates = dfxa['Date'].dt.strftime('%Y-%m-%d').sort_values().unique()
        sns.set(rc={'figure.figsize': (15, 5)})
        bar_plot.set_title('%s' % family)
        bar_plot.set_xticklabels(labels=dates, rotation=45, ha='right')
        bar_plot.get_figure().savefig('digest_files/resources/%s.png' % family)
        plt.close()


def exportIndex():
    dirs = [d for d in os.listdir('digested') if os.path.isdir('digested/' + d)]

    index_f = open("index.js", "w")
    index_f.write('data = %s' % json.dumps(dirs, indent=4, sort_keys=True))
    index_f.close()


#files = getListOfFiles('digest_files')
files = ['digest_files']
files.extend(['digest.js', 'digest.html'])

exportPlotPie(filtered_output)
exportFolder(Path(input_file).stem, files)
exportZIP(Path(input_file).stem, files)
exportIndex()

