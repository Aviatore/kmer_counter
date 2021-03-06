import os
import scipy.stats as stats
import pandas as pd
from statsmodels.sandbox.stats.multicomp import multipletests
from app.text_formating import red, green, print_info, print_warning, print_logo
import datetime
# EXAMPLE: multipletests([0.01, 0.02, 0.03], method='bonferroni')
# RETURNS: (array([ True, False, False]), array([0.03, 0.06, 0.09]), 0.016952427508441503, 0.016666666666666666)


class Stat:
    def __init__(self, parameters):
        datetime.datetime.now()
        self.parameters = parameters
        self.BONFERRONI_OUT_INDEX = 1
        self.chrom_len = {}
        self.total_genome_len = 0
        self.mite_total_len = {}
        self.index = []
        self.mite_names = {}
        self.column_names = ["mite_total_len", "mite", "out", "freq", "fisher_exac_p"]
        self.data = pd.DataFrame(columns=self.column_names)
        self.merged_table_path = os.path.join(parameters['output_dir'], 'tables', 'table_merged.txt')
        self.output_path = os.path.join(parameters['output_dir'], 'stats', 'stats.txt')

        if not os.path.exists(os.path.join(parameters['output_dir'], 'stats')):
            os.mkdir(os.path.join(parameters['output_dir'], 'stats'))

    def progress_bar(self, current_value, final_value):
        offset = 100
        diff = (current_value / final_value) * 100

        if not current_value % offset or current_value == final_value:
            print(f'\r\033[0K{current_value} / {final_value} ({diff:.2f}%)', end='', flush=True)

    def run(self):
        print_logo("Statistic analysis")

        if not os.path.exists(self.merged_table_path):
            print_warning("the merged table does not exist")
            return False

        if not os.path.exists(os.path.join(self.parameters['output_dir'], 'stats', 'stats.txt')) \
                or (os.path.exists(os.path.join(self.parameters['output_dir'], 'stats', 'stats.txt')) and self.parameters['keep_stats_file'] == 'no'):
            try:
                print_info("Applying Fisher test ...")
                self.chrom_len_calc()
                self.mite_total_len_calc()
                self.analyse()

                self.save_stats_to_file(os.path.join(self.parameters['output_dir'], 'stats', 'stats.txt'))
            except Exception:
                return False
        else:
            print_info(f"The output 'stats.txt' file exists. Loading saved data ... ")
            self.data = pd.read_csv(os.path.join(self.parameters['output_dir'], 'stats', 'stats.txt'), sep='\t')

        try:
            print("")
            print_info(f"Filter statistics data:")
            self.filter_kmers_by_p_corrected_bon_thresh()
            self.save_stats_to_file(os.path.join(self.parameters['output_dir'], 'stats', 'stats_filtered_1_corr_bonif_thresh.txt'))

            self.filter_kmers_by_freq_higher()
            self.save_stats_to_file(os.path.join(self.parameters['output_dir'], 'stats', 'stats_filtered_2_by_freq_higher.txt'))

            self.filter_kmers_by_freq_lesser()
            self.save_stats_to_file(os.path.join(self.parameters['output_dir'], 'stats', 'stats_filtered_3_by_freq_lesser.txt'))

            self.merge_coords_files()
            self.filter_coords_file()

            return True
        except Exception as e:
            print(f"Exception: {e}")
            return False

    def chrom_len_calc(self):
        for prefix in self.parameters['prefixes']:
            with open(os.path.join(self.parameters['data_dir'], f'{prefix}_oneLine.txt')) as file:
                line_len = 0

                for line in file:
                    line = line.rstrip()
                    line_len += len(line)

                self.chrom_len[prefix] = line_len
                self.total_genome_len += line_len

    def mite_total_len_calc(self):
        with open(self.parameters['bed_file'], 'r') as f:
            for line in f:
                line = line.rstrip()

                line_spliced = line.split('\t')

                try:
                    self.mite_total_len[line_spliced[-1]] += ( int(line_spliced[2]) - int(line_spliced[1]) + 1)
                except KeyError:
                    self.mite_total_len[line_spliced[-1]] = ( int(line_spliced[2]) - int(line_spliced[1]) + 1)

    def get_number_of_lines(self, file_name):
        with open(file_name, 'r') as file:
            for line_index, _ in enumerate(file):
                pass

        return line_index + 1

    def analyse(self):
        with open(self.merged_table_path, 'r') as f:
            number_of_lines = self.get_number_of_lines(self.merged_table_path)

            for line_numer, line in enumerate(f):
                self.progress_bar(line_numer + 1, number_of_lines)

                line = line.rstrip()

                kmers_in_mites_normalized = []
                kmers_out_mites_normalized = []
                kmers_in_mites_total_sum = 0
                mite_total_len_int = 0

                line_spliced = line.split('\t')

                if line_spliced[0] == "k-mer":
                    for i in range(2, len(line_spliced) - 2):
                        if line_spliced[i][-5:] != "_edge":
                            self.index.append(i)
                            self.mite_names[i] = line_spliced[i]
                else:
                    kmerName = line_spliced[0]
                    kmerTotalOccurences = int(line_spliced[1])
                    for i in self.index:
                        if int(line_spliced[i]) > 0:
                            kmers_in_mites_total_sum += int(line_spliced[i])
                            mite_total_len_int += self.mite_total_len[self.mite_names[i]]

                    if mite_total_len_int > 0:
                        a = round( (mite_total_len_int / self.total_genome_len) * kmerTotalOccurences )
                        b = round( ((self.total_genome_len - mite_total_len_int) / self.total_genome_len) * kmerTotalOccurences )

                        kmers_in_out_total_sum = kmerTotalOccurences - kmers_in_mites_total_sum

                        # print(kmerTotalOccurences, kmers_in_mites_total_sum)

                        _, p = stats.fisher_exact([[kmers_in_mites_total_sum, kmers_in_out_total_sum], [a, b]])

                        freq = kmers_in_mites_total_sum / (kmers_in_mites_total_sum + kmers_in_out_total_sum)

                        row = pd.Series([mite_total_len_int, kmers_in_mites_total_sum, kmers_in_out_total_sum, freq, p],
                                        name=kmerName, index=self.column_names)
                        self.data = self.data.append(row)

        print("")
        corrected_p = multipletests(list(self.data['fisher_exac_p']), method='bonferroni')[self.BONFERRONI_OUT_INDEX]

        self.data['p_corrected_bon'] = corrected_p

    def filter_kmers_by_p_corrected_bon_thresh(self):
        print(f"- filtering by bonferoni ... ", end='')
        self.data = self.data.loc[self.data['p_corrected_bon'] <= float(self.parameters['p_corrected_bon_thresh'])]

        print(green('ok'))

    def filter_kmers_by_freq_higher(self):
        print(f"- filtering by freq higher ... ", end='')

        if self.parameters['kmer_thresh_min'] != '':
            self.data = self.data.loc[self.data['freq'] > (self.data['mite_total_len'] / self.total_genome_len) * int(self.parameters['kmer_thresh_min'])]

        print(green('ok'))

    def filter_kmers_by_freq_lesser(self):
        print(f"- filtering by freq lesser ... ", end='')
        if self.parameters['kmer_thresh_max'] != '':
            self.data = self.data.loc[self.data['freq'] < (self.data['mite_total_len'] / self.total_genome_len) * int(self.parameters['kmer_thresh_max'])]

        print(green('ok'))

    def stats_filtration(self):
        # TODO Second filtration step: All data wich freq is out of provided threshold range must be filtered out
        self.filter_kmers_by_p_corrected_bon_thresh()

        self.filter_kmers_by_freq_higher()

        self.filter_kmers_by_freq_lesser()

        return self.data

    def merge_coords_files(self):
        with open(os.path.join(self.parameters['output_dir'], 'tables', 'table_coords_merged.txt'), 'w') as output:
            for prefix in self.parameters['prefixes']:
                with open(os.path.join(self.parameters['output_dir'], 'tables', f'table_{prefix}_coords.txt'), 'r') as file:
                    for line in file:
                        output.write(line)

    def filter_coords_file(self):
        kmers = dict.fromkeys(list(self.data.index), 0)

        with open(os.path.join(self.parameters['output_dir'], 'tables', 'table_coords_merged_filtered.txt'), 'w') as output:
            with open(os.path.join(self.parameters['output_dir'], 'tables', 'table_coords_merged.txt'), 'r') as file:
                for line in file:
                    line_splitted = line.rstrip().split("\t")
                    kmer = line_splitted[3].split(";")[0]

                    if kmer in kmers:
                        output.write(line)

    def save_stats_to_file(self, filename):
        print_info(f"Saving data to file '{os.path.basename(filename)}'")
        self.data.to_csv(filename, sep='\t')
