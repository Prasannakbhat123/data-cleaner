import pandas as pd
import numpy as np
import json
from datetime import datetime

try:
    from fuzzywuzzy import process
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False
    print("Warning: fuzzywuzzy not available. Typo correction will be disabled.")

class DataCleaningBot:
    def __init__(self, filepath):
        self.df = pd.read_csv(filepath)
        self.df.columns = self.df.columns.str.strip()
        self.df.columns = self.df.columns.str.lower()
        print("Columns in DataFrame:", self.df.columns.tolist())
        self.log = []

    def handle_missing_values(self, strategy='mean'):
        for col in self.df.columns:
            if self.df[col].isnull().sum() > 0:
                before = self.df[col].isnull().sum()
                if self.df[col].dtype in ['float64', 'int64']:
                    fill_value = self.df[col].mean() if strategy == 'mean' else self.df[col].median()
                    self.df.fillna({col: fill_value}, inplace=True)
                else:
                    self.df.fillna({col: self.df[col].mode()[0]}, inplace=True)
                after = self.df[col].isnull().sum()
                self.log.append({"missing_values_fixed": {"column": col, "before": int(before), "after": int(after)}})
                print(f"Missing values fixed in '{col}': before={before}, after={after}")

    def fix_dtypes(self):
        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                if 'date' in col.lower() or col.lower() in ['join date', 'joindate', 'date_joined']:
                    try:
                        parsed_dates = pd.to_datetime(self.df[col], errors='coerce', dayfirst=True)
                    except Exception:
                        parsed_dates = pd.to_datetime(self.df[col], errors='coerce')
                    
                    if parsed_dates.notna().mean() > 0.8:
                        formatted_dates = []
                        for date_val in parsed_dates:
                            if pd.isna(date_val):
                                formatted_dates.append(np.nan)
                            else:
                                formatted_dates.append(date_val.strftime('%d/%m/%Y'))
                        
                        self.df[col] = formatted_dates
                        self.log.append({"dtype_fix": {"column": col, "new_type": "datetime_formatted"}})
                        self.log.append({"format_fix": {"column": col, "format": "dd/mm/yyyy"}})
                        print(f"Data type fixed for '{col}' and formatted to 'dd/mm/yyyy'.")
                else:
                    numeric_parsed = pd.to_numeric(self.df[col], errors='coerce')
                    if numeric_parsed.notna().mean() > 0.8:
                        self.df[col] = numeric_parsed
                        self.log.append({"dtype_fix": {"column": col, "new_type": "numeric"}})
                        print(f"Data type fixed for '{col}' to numeric.")

    def remove_duplicates(self):
        duplicate_indices = self.df[self.df.duplicated()].index.tolist()
        before = len(duplicate_indices)
        self.df.drop_duplicates(inplace=True)
        if before > 0:
            self.log.append({"duplicates_removed": {"count": before, "indices": duplicate_indices}})
            print(f"Duplicates removed: {before} rows at indices {duplicate_indices}")
        else:
            print("No duplicates found.")

    def trim_whitespace(self):
        for col in self.df.select_dtypes(include='object').columns:
            if self.df[col].apply(lambda x: isinstance(x, str) and (x.startswith(' ') or x.endswith(' '))).any():
                self.df[col] = self.df[col].str.strip()
                self.log.append({"trim_whitespace": col})
                print(f"Whitespace trimmed in column '{col}'.")

    def lowercase_columns(self):
        for col in self.df.select_dtypes(include='object').columns:
            if 'date' in col.lower():
                continue
            if any(isinstance(x, str) and not x.islower() for x in self.df[col]):
                self.df[col] = self.df[col].str.lower()
                self.log.append({"lowercase": col})
                print(f"Converted column '{col}' to lowercase.")

    def detect_outliers(self):
        outliers_info = {}
        for col in self.df.select_dtypes(include=['float64', 'int64']).columns:
            q1 = self.df[col].quantile(0.25)
            q3 = self.df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outlier_indices = self.df[(self.df[col] < lower) | (self.df[col] > upper)].index.tolist()
            if outlier_indices:
                outliers_info[col] = outlier_indices
        if outliers_info:
            self.log.append({"outliers_detected": outliers_info})
            print(f"Outliers detected: {outliers_info}")
        else:
            print("No outliers detected.")

    def correct_typos(self, column, valid_values):
        if not FUZZYWUZZY_AVAILABLE:
            print("Typo correction skipped - fuzzywuzzy not installed")
            return
            
        corrected = {}
        if column not in self.df.columns:
            print(f"Column '{column}' does not exist in the DataFrame.")
            return
        for val in self.df[column].dropna().unique():
            match, score = process.extractOne(str(val), valid_values)
            if score > 80 and str(val) != match:
                self.df[column] = self.df[column].replace(val, match)
                corrected[val] = match
        if corrected:
            self.log.append({"typos_corrected": {column: corrected}})
            print(f"Typos corrected in column '{column}': {corrected}")
        else:
            print(f"No typos corrected in column '{column}'.")

    def save_cleaned_data(self, output_path):
        self.df.to_csv(output_path, index=False)
        print(f"Cleaned data saved to '{output_path}'.")

    def save_log(self, log_path):
        with open(log_path, 'w') as f:
            json.dump(self.log, f, indent=2)
        print(f"Cleaning log saved to '{log_path}'.")

    def summary_report(self):
        print("\n=== Summary Report ===")
        print(f"Total Rows: {self.df.shape[0]}")
        print(f"Total Columns: {self.df.shape[1]}")
        print("Column Types:")
        print(self.df.dtypes)
        print("Missing Values per Column:")
        print(self.df.isnull().sum())
        print("=======================\n")
