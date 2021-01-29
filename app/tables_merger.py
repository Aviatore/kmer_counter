import re
import numpy as np
import os


class TableMerger:
    def __init__(self, parameters):
        self.parameters = parameters
        self.output_path = os.path.join(self.parameters['output_dir'], 'tables')
        self.merged_data = {}

    def run(self):
        self.merge_tables()
        self.write_merged_tables()

    def merge_tables(self):
        lineSplit = re.compile(r'\t')

        if (os.path.exists(os.path.join(self.output_path, 'table_merged.txt'))):
            os.remove(os.path.join(self.output_path, 'table_merged.txt'))

        for table in self.get_all_table_files():
            print("Reading", table, "...")

            with open(os.path.join(self.output_path, table), 'r') as f:
                while True:
                    line = f.readline()
                    if line is "":
                        break

                    line = line.rstrip()
                    line_splitted = lineSplit.split(line)
                    if line_splitted[0] == "k-mer":
                        self.merged_data["header"] = line
                        continue

                    line_splitted[1:] = list(map(int, line_splitted[1:]))
                    try:
                        self.merged_data[line_splitted[0]] += np.array(line_splitted[1:])
                    except KeyError:
                        self.merged_data[line_splitted[0]] = np.array(line_splitted[1:])

    def get_all_table_files(self):
        tables = []
        prefixes = self.parameters['prefixes'].split(",")

        for file in os.listdir(self.output_path):
            if file.split("_")[-1] in prefixes:
                tables.append(file)

        return tables

    def write_merged_tables(self):
        with open(os.path.join(self.output_path, "table_merged.txt"), 'a+') as f:
            f.write(self.merged_data.pop("header", None) + "\n")

            for kmer in sorted(self.merged_data.keys()):
                f.write(kmer + "\t" + "\t".join(list(map(str, self.merged_data[kmer]))) + "\n")
